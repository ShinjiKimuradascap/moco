import json
import os
import random
from enum import Enum
from typing import List, Dict, Any, Optional

try:
    from .formulas import (
        Attribute, 
        calculate_success_rate, 
        judge_action, 
        get_attribute_modifier,
        get_stamina_modifier
    )
except (ImportError, ValueError):
    from formulas import (
        Attribute, 
        calculate_success_rate, 
        judge_action, 
        get_attribute_modifier,
        get_stamina_modifier
    )

class MatchState(Enum):
    SERVE = "SERVE"
    RECEIVE = "RECEIVE"
    TOSS = "TOSS"
    ATTACK = "ATTACK"
    BLOCK_DIG = "BLOCK_DIG"
    RESULT = "RESULT"

class Player:
    def __init__(self, data: Dict[str, Any]):
        self.id = data["id"]
        self.name = data["name"]
        self.position = data["position"]
        self.stats = data["stats"]
        self.current_stamina = self.stats["stamina"]
        self.max_stamina = self.stats["stamina"]
        # デフォルト属性（本来はマスタに持たせるが、シミュレーション用に設定）
        self.attribute = Attribute.POWER if "日向" in self.name else Attribute.TECHNIQUE

    def get_stat(self, key: str) -> float:
        base = self.stats.get(key, 50)
        mod = get_stamina_modifier(self.current_stamina, self.max_stamina)
        return base * mod

class MatchEngine:
    def __init__(self, team_a: List[Player], team_b: List[Player]):
        self.team_a = team_a
        self.team_b = team_b
        self.state = MatchState.SERVE
        self.logs = []

    def log(self, message: str):
        print(message)
        self.logs.append(message)

    def simulate_rally(self, server: Player, receiver: Player, blocker: Player):
        self.log(f"--- Rally Start: {server.name} vs {receiver.name} ---")
        
        # 1. SERVE vs RECEIVE
        self.state = MatchState.SERVE
        self.log(f"[{self.state.value}] {server.name} のサーブ！")
        
        attr_mod = get_attribute_modifier(server.attribute, receiver.attribute)
        p_serve = calculate_success_rate(
            server.get_stat("serve"), 
            receiver.get_stat("receive"),
            attribute_modifier=attr_mod
        )
        
        # 簡易的に、サーブ側が成功（エースまたは崩す）かどうか
        if judge_action(p_serve):
            self.log(f"-> {server.name} の強力なサーブが炸裂！")
            success_mult = 1.2
        else:
            self.log(f"-> {receiver.name} が綺麗にレシーブした！")
            success_mult = 0.8

        # 2. TOSS (簡易化: セッターがいない場合は自己トス扱い)
        self.state = MatchState.TOSS
        self.log(f"[{self.state.value}] トスが上がる...")

        # 3. ATTACK vs BLOCK
        self.state = MatchState.ATTACK
        self.log(f"[{self.state.value}] {server.name} のアタック vs {blocker.name} のブロック！")
        
        # 日向（スピード型と仮定）vs 影山（テクニック型と仮定）
        # シミュレーション用に一時的に属性変更
        attacker_attr = Attribute.SPEED if "日向" in server.name else Attribute.POWER
        blocker_attr = Attribute.TECHNIQUE if "影山" in blocker.name else Attribute.SPEED
        
        attr_mod_atk = get_attribute_modifier(attacker_attr, blocker_attr)
        
        p_attack = calculate_success_rate(
            server.get_stat("spike"),
            blocker.get_stat("block"),
            atk_skill_mult=success_mult, # サーブの結果による補正
            attribute_modifier=attr_mod_atk
        )

        if judge_action(p_attack):
            self.log(f"-> {server.name} のスパイクが決まった！！ 得点。")
            self.state = MatchState.RESULT
            return "POINT"
        else:
            self.log(f"-> {blocker.name} がシャットアウト！ またはワンタッチ。")
            self.state = MatchState.RESULT
            return "BLOCK"

def load_master_data(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

if __name__ == "__main__":
    # パス解決
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../../../"))
    master_path = os.path.join(project_root, "haikyu_project/data/character_master.json")
    
    characters = load_master_data(master_path)
    hinata_data = next(c for c in characters if "日向" in c["name"])
    kageyama_data = next(c for c in characters if "影山" in c["name"])

    hinata = Player(hinata_data)
    kageyama = Player(kageyama_data)

    engine = MatchEngine([hinata], [kageyama])
    
    # 影山サーブ vs 日向レシーブ、日向アタック vs 影山ブロックのシミュレーション
    # (1対1なので便宜上の配役)
    engine.simulate_rally(server=kageyama, receiver=hinata, blocker=hinata)
    print("\n--- 次のラリー ---\n")
    engine.simulate_rally(server=hinata, receiver=kageyama, blocker=kageyama)
