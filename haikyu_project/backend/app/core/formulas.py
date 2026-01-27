import random
from enum import Enum

class Attribute(Enum):
    POWER = "POWER"    # 剛
    TECHNIQUE = "TECHNIQUE"  # 柔
    SPEED = "SPEED"    # 瞬

def get_attribute_modifier(attacker_attr: Attribute, defender_attr: Attribute) -> float:
    """属性相性の補正値を返す。
    剛(POWER) > 瞬(SPEED) > 柔(TECHNIQUE) > 剛(POWER)
    """
    if attacker_attr == defender_attr:
        return 1.0
    
    # 有利な組み合わせ
    win_map = {
        Attribute.POWER: Attribute.SPEED,
        Attribute.SPEED: Attribute.TECHNIQUE,
        Attribute.TECHNIQUE: Attribute.POWER
    }
    
    if win_map[attacker_attr] == defender_attr:
        return 1.2  # 有利: +20%
    else:
        return 0.8  # 不利: -20%

def get_stamina_modifier(current_stamina: int, max_stamina: int) -> float:
    """スタミナによるパフォーマンス係数を返す。
    スタミナが20%以下ならパフォーマンスが急激に低下する例。
    """
    ratio = current_stamina / max_stamina if max_stamina > 0 else 0
    if ratio > 0.5:
        return 1.0
    elif ratio > 0.2:
        return 0.9
    else:
        return 0.7

def calculate_success_rate(
    atk_stat: float, 
    def_stat: float, 
    atk_skill_mult: float = 1.0, 
    def_skill_mult: float = 1.0,
    atk_condition: float = 1.0,
    def_condition: float = 1.0,
    attribute_modifier: float = 1.0
) -> float:
    """基本成功率 P を計算する。
    P = (A_stat * A_skill * A_cond) / (D_stat * D_skill * D_cond) * AttrMod
    """
    numerator = atk_stat * atk_skill_mult * atk_condition
    denominator = def_stat * def_skill_mult * def_condition
    
    if denominator == 0:
        return 2.0  # ほぼ確実に成功
        
    base_p = (numerator / denominator) * attribute_modifier
    return base_p

def judge_action(success_rate: float, random_range: tuple = (0.9, 1.1)) -> bool:
    """乱数を含めてアクションの成否を判定する。"""
    final_p = success_rate * random.uniform(*random_range)
    # 成功率 1.0 (100%) を超えれば成功しやすくなるが、基本は 1.0 を閾値とする
    return final_p >= 1.0
