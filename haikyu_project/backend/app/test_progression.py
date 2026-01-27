from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import User, Character
from core.progression import CharacterProgression, EconomyManager
import datetime
import time

# テーブル作成
Base.metadata.create_all(bind=engine)

def test_progression():
    db = SessionLocal()
    try:
        # テストユーザー作成
        test_user = User(
            name="Hinata", 
            free_wings=1000, 
            gold=5000, 
            stamina=50, 
            last_stamina_update=datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        
        print(f"Initial User: {test_user.name}, Gold: {test_user.gold}, Stamina: {test_user.stamina}")

        # スタミナ同期テスト (30分経過 -> 6回復のはず)
        EconomyManager.sync_stamina(db, test_user.id)
        print(f"Synced Stamina: {test_user.stamina} (Expected 56)")

        # 通貨消費テスト
        success, user = EconomyManager.consume_currency(db, test_user.id, "gold", 1000)
        print(f"Consume Gold Success: {success}, New Gold: {user.gold}")

        # キャラクター育成テスト
        char = Character(user_id=test_user.id, master_id=10, level=1, exp=0, shards=100)
        db.add(char)
        db.commit()
        db.refresh(char)

        print(f"Initial Char Level: {char.level}, Exp: {char.exp}")
        
        # 経験値付与 (1級レベルアップに必要な 100 * 1^1.5 = 100 を超える量を付与)
        CharacterProgression.add_exp(db, char.id, 500)
        print(f"Level Up Char: Level {char.level}, Exp: {char.exp}")

        # スターランクアップ
        success, result = CharacterProgression.star_up(db, char.id)
        if success:
            print(f"Star Up Success: New Rank {result.star_rank}, Remaining Shards: {result.shards}")
        else:
            print(f"Star Up Failed: {result}")

    finally:
        db.close()

if __name__ == "__main__":
    test_progression()
