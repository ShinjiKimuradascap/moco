from typing import Dict, List, Optional, Tuple
from enum import Enum
import random

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

class Position(Enum):
    P1 = 1  # 後衛右 (サーブ位置)
    P2 = 2  # 前衛右
    P3 = 3  # 前衛中央 (セッター/MB)
    P4 = 4  # 前衛左
    P5 = 5  # 後衛左
    P6 = 6  # 後衛中央

class MatchState(Enum):
    SERVE = "SERVE"
    RECEIVE = "RECEIVE"
    TOSS = "TOSS"
    SPIKE = "SPIKE"
    BLOCK = "BLOCK"
    DIG = "DIG"
    POINT = "POINT"

class PlayerProxy:
    """試合中のプレイヤー状態を管理するプロキシクラス"""
    def __init__(self, data: dict):
        self.id = data.get("id")
        self.name = data.get("name", "Unknown")
        self.role = data.get("position", "WS") # WS, MB, S, L
        self.stats = data.get("stats", {})
        self.attribute = data.get("attribute", Attribute.TECHNIQUE)
        self.max_stamina = self.stats.get("stamina", 100)
        self.current_stamina = self.max_stamina

    def get_stat(self, key: str) -> float:
        base = self.stats.get(key, 50)
        mod = get_stamina_modifier(self.current_stamina, self.max_stamina)
        return base * mod

    def consume_stamina(self, amount: int):
        self.current_stamina = max(0, self.current_stamina - amount)

class TeamFormation:
    """チームの編成、ローテーション、リベロ交代を管理"""
    def __init__(self, name: str, players: Dict[int, PlayerProxy], libero: Optional[PlayerProxy] = None):
        # players は {1: p1, 2: p2, ..., 6: p6} の辞書形式 (オリジナルの選手)
        self.name = name
        self.players = players # オリジナルの6人
        self.libero = libero
        self.active_libero_pos = None # リベロが現在入っているポジション (1-6)

    def rotate(self):
        """時計回りにローテーションを行う (1 -> 6 -> 5 -> 4 -> 3 -> 2 -> 1)
        Pos 2 moves to 1, 3 to 2, ..., 1 to 6.
        """
        p = self.players
        old_1 = p[1]
        p[1] = p[2]
        p[2] = p[3]
        p[3] = p[4]
        p[4] = p[5]
        p[5] = p[6]
        p[6] = old_1

        # リベロの位置も移動する
        if self.active_libero_pos is not None:
            # 2 -> 1, 3 -> 2, 4 -> 3, 5 -> 4, 6 -> 5, 1 -> 6
            new_pos = self.active_libero_pos - 1
            if new_pos == 0:
                new_pos = 6
            self.active_libero_pos = new_pos

        self.apply_libero_substitution()

    def apply_libero_substitution(self):
        """リベロ交代ロジックの適用"""
        if not self.libero:
            return

        # 1. リベロが前衛(2,3,4)に移動してしまったら、コートから出す
        if self.active_libero_pos in [2, 3, 4]:
            self.active_libero_pos = None

        # 2. 後衛(1,5,6)にMBがいて、リベロがコートにいないなら、交代する
        # ※本来はMB2人とも交代するが、ここでは「リベロは常に1人」を優先
        if self.active_libero_pos is None:
            for pos in [1, 5, 6]:
                if self.players[pos].role == "MB":
                    self.active_libero_pos = pos
                    break

    def get_player_in_pos(self, pos: int) -> PlayerProxy:
        if self.active_libero_pos == pos:
            return self.libero
        return self.players[pos]

class MatchLogic:
    """試合の進行ロジック"""
    def __init__(self, team_a: TeamFormation, team_b: TeamFormation):
        self.team_a = team_a
        self.team_b = team_b
        self.logs = []

    def log(self, msg: str):
        self.logs.append(msg)

    def execute_rally(self, serving_team: TeamFormation, receiving_team: TeamFormation) -> TeamFormation:
        """1ラリーの実行。勝利したチームを返す。"""
        # --- PHASE 1: SERVE ---
        server = serving_team.get_player_in_pos(1)
        self.log(f"[{serving_team.name}] {server.name} のサーブ！")
        
        # レシーバーの選定（簡易的に後衛の誰か）
        receiver_pos = random.choice([1, 5, 6])
        receiver = receiving_team.get_player_in_pos(receiver_pos)
        
        # --- PHASE 2: RECEIVE ---
        success_rate = calculate_success_rate(
            server.get_stat("serve"),
            receiver.get_stat("receive"),
            attribute_modifier=get_attribute_modifier(server.attribute, receiver.attribute)
        )
        
        is_receive_success = judge_action(success_rate)
        toss_quality = 1.2 if is_receive_success else 0.8
        self.log(f"[{receiving_team.name}] {receiver.name} のレシーブ: {'成功' if is_receive_success else '乱れた'}")

        # --- PHASE 3: TOSS ---
        # セッターを探す（いなければ適当な前衛）
        setter = next((p for p in [receiving_team.get_player_in_pos(i) for i in [2,3,4]] if p.role == "S"), 
                      receiving_team.get_player_in_pos(3))
        self.log(f"[{receiving_team.name}] {setter.name} のトス！")

        # --- PHASE 4: SPIKE ---
        # アタッカーの選定（前衛 2, 3, 4 からランダム）
        attacker_pos = random.choice([2, 3, 4])
        attacker = receiving_team.get_player_in_pos(attacker_pos)
        
        # --- PHASE 5: BLOCK ---
        # ブロッカーの選定（相手チームの前衛から対面、ここでは簡易的に前衛中央）
        blocker = serving_team.get_player_in_pos(3)
        
        spike_success_rate = calculate_success_rate(
            attacker.get_stat("spike"),
            blocker.get_stat("block"),
            atk_skill_mult=toss_quality,
            attribute_modifier=get_attribute_modifier(attacker.attribute, blocker.attribute)
        )
        
        is_spike_down = judge_action(spike_success_rate)
        
        if is_spike_down:
            self.log(f"[{receiving_team.name}] {attacker.name} のスパイクが決まった！")
            return receiving_team
        else:
            # --- PHASE 6: DIG ---
            # ブロックされた、あるいは拾われた場合
            self.log(f"[{serving_team.name}] {blocker.name} がワンタッチ！")
            
            # ディグ判定（後衛が拾えるか）
            digger = serving_team.get_player_in_pos(random.choice([1, 5, 6]))
            dig_success_rate = calculate_success_rate(
                attacker.get_stat("spike") * 0.7, # 弱まったスパイク
                digger.get_stat("receive")
            )
            
            if judge_action(dig_success_rate):
                self.log(f"[{serving_team.name}] {digger.name} が繋いだ！ラリー継続（シミュレーション上は得点なしで再試行）")
                # 再帰的にラリーを続けても良いが、無限ループを避けるためここでは確率で決着
                if random.random() > 0.5:
                    self.log(f"長いラリーの末、{serving_team.name} が得点！")
                    return serving_team
                else:
                    self.log(f"長いラリーの末、{receiving_team.name} が得点！")
                    return receiving_team
            else:
                self.log(f"[{serving_team.name}] レシーブ失敗。{receiving_team.name} の得点。")
                return receiving_team
