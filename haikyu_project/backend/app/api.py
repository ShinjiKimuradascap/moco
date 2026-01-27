from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import random

from .database import get_db
from .models import User, Character, Team, Item
from .schemas import (
    GachaRequest, GachaResponse, GachaResultItem,
    MatchRequest, MatchResponse,
    LevelUpRequest, StarUpRequest,
    UserStatusResponse, UserBase, CharacterBase, ItemBase
)
from .core.gacha_engine import GachaEngine
from .core.match_logic import MatchLogic, TeamFormation, PlayerProxy
from .core.progression import CharacterProgression, EconomyManager

router = APIRouter()

@router.get("/user/status", response_model=UserStatusResponse)
def get_user_status(user_id: int, db: Session = Depends(get_db)):
    # スタミナ自動回復を同期
    user = EconomyManager.sync_stamina(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user

@router.post("/gacha/draw", response_model=GachaResponse)
def draw_gacha(req: GachaRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 通貨チェック (1回300ウィングと仮定)
    cost = 300 * req.times
    success, user = EconomyManager.consume_currency(db, req.user_id, "wings", cost)
    if not success:
        raise HTTPException(status_code=400, detail="Insufficient wings")

    engine = GachaEngine()
    gacha_result = engine.draw_gacha(str(req.user_id), user.mileage, req.times)
    
    # ユーザーのマイレージを更新
    user.mileage = gacha_result["new_pull_count"]
    db.commit()

    response_items = []
    for res in gacha_result["results"]:
        # 簡易マスタID決定 (本来はレアリティに対応したマスタから抽選)
        master_id = random.randint(1001, 1100)
        
        # すでに所持しているか確認
        char = db.query(Character).filter(
            Character.user_id == req.user_id,
            Character.master_id == master_id
        ).first()

        is_new = False
        if char:
            # 重複時は欠片に変換 (Iconic: 50, Gold: 20, Silver: 5, Normal: 1 と仮定)
            shard_map = {"Iconic": 50, "Gold": 20, "Silver": 5, "Normal": 1}
            char.shards += shard_map.get(res["rarity"], 1)
        else:
            # 新規獲得
            new_char = Character(
                user_id=req.user_id,
                master_id=master_id,
                level=1,
                exp=0,
                star_rank=1,
                shards=0
            )
            db.add(new_char)
            is_new = True
        
        response_items.append(GachaResultItem(
            rarity=res["rarity"],
            detail=res["detail"],
            master_id=master_id,
            is_new=is_new
        ))

    db.commit()
    return GachaResponse(
        results=response_items,
        new_mileage=user.mileage
    )

@router.post("/match/simulate", response_model=MatchResponse)
def simulate_match(req: MatchRequest, db: Session = Depends(get_db)):
    # スタミナ消費
    success, user = EconomyManager.consume_stamina(db, req.user_id, 10)
    if not success:
        raise HTTPException(status_code=400, detail="Insufficient stamina")

    # チー厶取得
    team = db.query(Team).filter(Team.id == req.team_id, Team.user_id == req.user_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # 本来はDBの所属キャラから PlayerProxy を作るが、ここでは簡易的にモック
    def create_mock_player(name, role):
        return PlayerProxy({
            "id": random.randint(1, 1000), "name": name, "position": role,
            "stats": {"serve": 60, "receive": 60, "toss": 60, "spike": 70, "block": 50, "stamina": 100}
        })

    players = {i: create_mock_player(f"Player {i}", "WS") for i in range(1, 7)}
    players[3] = create_mock_player("Mock MB", "MB")
    libero = create_mock_player("Mock Libero", "L")
    
    formation_a = TeamFormation(team.name, players, libero)
    
    # 対戦相手 (Mock)
    opp_players = {i: create_mock_player(f"Opp {i}", "WS") for i in range(1, 7)}
    formation_b = TeamFormation("Opponent Team", opp_players)

    logic = MatchLogic(formation_a, formation_b)
    winner = logic.execute_rally(formation_a, formation_b)
    
    is_win = (winner == formation_a)
    
    # 報酬付与
    gold_reward = 500 if is_win else 100
    exp_reward = 200 if is_win else 50
    
    EconomyManager.add_currency(db, req.user_id, "gold", gold_reward)
    # 所持キャラ全員にEXP (本来は編成キャラのみ)
    user_chars = db.query(Character).filter(Character.user_id == req.user_id).all()
    for char in user_chars:
        CharacterProgression.add_exp(db, char.id, exp_reward)

    return MatchResponse(
        is_win=is_win,
        logs=logic.logs,
        rewards={"gold": gold_reward, "exp": exp_reward}
    )

@router.post("/character/level_up")
def level_up(req: LevelUpRequest, db: Session = Depends(get_db)):
    # ゴールド消費
    success, _ = EconomyManager.consume_currency(db, req.user_id, "gold", req.gold_cost)
    if not success:
        raise HTTPException(status_code=400, detail="Insufficient gold")

    char = CharacterProgression.add_exp(db, req.character_id, req.exp_amount)
    return {"status": "success", "new_level": char.level, "new_exp": char.exp}

@router.post("/character/star_up")
def star_up(req: StarUpRequest, db: Session = Depends(get_db)):
    success, result = CharacterProgression.star_up(db, req.character_id)
    if not success:
        raise HTTPException(status_code=400, detail=result)
    
    return {"status": "success", "new_star_rank": result.star_rank}
