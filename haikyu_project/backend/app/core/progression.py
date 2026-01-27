import datetime
from sqlalchemy.orm import Session
from ..models import User, Character, Item

class CharacterProgression:
    """キャラクターのレベルアップとランクアップ（StarUp）を管理するクラス"""

    @staticmethod
    def add_exp(db: Session, character_id: int, exp_amount: int):
        """キャラクターに経験値を与え、必要に応じてレベルアップさせる。"""
        char = db.query(Character).filter(Character.id == character_id).first()
        if not char:
            raise ValueError(f"Character {character_id} not found")

        char.exp += exp_amount
        
        # レベルアップのループ
        while True:
            # 簡略化したレベルアップ必要経験値式: 100 * (current_level ^ 1.5)
            next_level_exp = int(100 * (char.level ** 1.5))
            if char.exp >= next_level_exp:
                char.exp -= next_level_exp
                char.level += 1
            else:
                break
        
        db.commit()
        db.refresh(char)
        return char

    @staticmethod
    def star_up(db: Session, character_id: int):
        """欠片を消費してスターランクを上げる。
        ランクアップに必要な欠片の例: 1->2(20), 2->3(50), 3->4(100), 4->5(200)
        """
        char = db.query(Character).filter(Character.id == character_id).first()
        if not char:
            raise ValueError(f"Character {character_id} not found")

        shard_requirements = {
            1: 20,
            2: 50,
            3: 100,
            4: 200,
            5: 400
        }
        
        needed = shard_requirements.get(char.star_rank, 9999)
        if char.shards < needed:
            return False, f"Not enough shards: {char.shards}/{needed}"

        char.shards -= needed
        char.star_rank += 1
        
        db.commit()
        db.refresh(char)
        return True, char

class EconomyManager:
    """経済システム（通貨・スタミナ）を管理するクラス"""

    STAMINA_RECOVERY_INTERVAL_MIN = 5  # 5分で1回復
    STAMINA_CAP = 100
    STAMINA_COST_PER_WINGS = 10 # 10石で全回復などのロジック用（ここでは仮）

    @staticmethod
    def sync_stamina(db: Session, user_id: int):
        """時間経過によるスタミナ回復を計算・適用する。"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        now = datetime.datetime.utcnow()
        if user.stamina < EconomyManager.STAMINA_CAP:
            delta = now - user.last_stamina_update
            minutes_passed = int(delta.total_seconds() / 60)
            recovery_amount = minutes_passed // EconomyManager.STAMINA_RECOVERY_INTERVAL_MIN
            
            if recovery_amount > 0:
                user.stamina = min(EconomyManager.STAMINA_CAP, user.stamina + recovery_amount)
                # 分単位で丸めて最後の更新日時を調整
                actual_recovered_minutes = recovery_amount * EconomyManager.STAMINA_RECOVERY_INTERVAL_MIN
                user.last_stamina_update += datetime.timedelta(minutes=actual_recovered_minutes)
                db.commit()
                db.refresh(user)
        else:
            # キャップを超えている場合は更新日時だけ現在にする（自然回復を止める）
            user.last_stamina_update = now
            db.commit()
        
        return user

    @staticmethod
    def consume_stamina(db: Session, user_id: int, amount: int):
        """スタミナを消費する。"""
        user = EconomyManager.sync_stamina(db, user_id)
        if user.stamina < amount:
            return False, "Not enough stamina"
        
        user.stamina -= amount
        db.commit()
        db.refresh(user)
        return True, user

    @staticmethod
    def consume_currency(db: Session, user_id: int, currency_type: str, amount: int):
        """各種通貨を消費する。
        currency_type: 'gold', 'wings', 'mileage'
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        if currency_type == 'gold':
            if user.gold < amount:
                return False, "Not enough gold"
            user.gold -= amount
        elif currency_type == 'wings':
            # 有償から先に使うか、無償から先に使うかは仕様によるが、一般的には無償から。
            total_wings = user.paid_wings + user.free_wings
            if total_wings < amount:
                return False, "Not enough wings"
            
            # 無償から消費
            if user.free_wings >= amount:
                user.free_wings -= amount
            else:
                remaining = amount - user.free_wings
                user.free_wings = 0
                user.paid_wings -= remaining
        elif currency_type == 'mileage':
            if user.mileage < amount:
                return False, "Not enough mileage"
            user.mileage -= amount
        else:
            return False, "Invalid currency type"

        db.commit()
        db.refresh(user)
        return True, user

    @staticmethod
    def add_currency(db: Session, user_id: int, currency_type: str, amount: int, is_paid=False):
        """通貨を付与する。"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        if currency_type == 'gold':
            user.gold += amount
        elif currency_type == 'wings':
            if is_paid:
                user.paid_wings += amount
            else:
                user.free_wings += amount
        elif currency_type == 'mileage':
            user.mileage += amount
        
        db.commit()
        db.refresh(user)
        return user
