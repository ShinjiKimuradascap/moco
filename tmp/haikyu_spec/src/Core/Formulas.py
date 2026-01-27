def calculate_match_rate(attacker_stat, defender_stat, skill_mult=1.0, attr_mod=1.0, condition=1.0):
    """
    基本成功判定式:
    Rate = (AttackerStat * Mult * Condition) / (DefenderStat * Condition) * AttrMod
    """
    a_final = attacker_stat * skill_mult * condition
    d_final = defender_stat * condition
    
    if d_final == 0: return 2.0 # 必中
    
    rate = (a_final / d_final) * attr_mod
    return rate

def get_attribute_modifier(atk_attr, def_attr):
    """
    属性相性: 剛(Power) > 瞬(Speed) > 柔(Technique) > 剛
    """
    mapping = {"Power": 0, "Speed": 1, "Technique": 2}
    # 0 > 1, 1 > 2, 2 > 0
    if (mapping[atk_attr] == 0 and mapping[def_attr] == 1) or \
       (mapping[atk_attr] == 1 and mapping[def_attr] == 2) or \
       (mapping[atk_attr] == 2 and mapping[def_attr] == 0):
        return 1.2 # 有利
    elif atk_attr == def_attr:
        return 1.0 # 等倍
    else:
        return 0.8 # 不利
