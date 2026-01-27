from match_logic import TeamFormation, PlayerProxy, MatchLogic, Position
from formulas import Attribute

def test_rotation_and_libero():
    # テスト用データ
    players_data = {
        1: {"id": 1, "name": "Hinata", "position": "MB", "stats": {"stamina": 100, "spike": 80, "receive": 40, "serve": 60, "block": 70}},
        2: {"id": 2, "name": "Kageyama", "position": "S", "stats": {"stamina": 100, "spike": 70, "receive": 70, "serve": 85, "block": 75}},
        3: {"id": 3, "name": "Tsukishima", "position": "MB", "stats": {"stamina": 100, "spike": 75, "receive": 40, "serve": 55, "block": 90}},
        4: {"id": 4, "name": "Tanaka", "position": "WS", "stats": {"stamina": 100, "spike": 85, "receive": 60, "serve": 70, "block": 60}},
        5: {"id": 5, "name": "Asahi", "position": "WS", "stats": {"stamina": 100, "spike": 90, "receive": 55, "serve": 80, "block": 65}},
        6: {"id": 6, "name": "Daichi", "position": "WS", "stats": {"stamina": 100, "spike": 75, "receive": 95, "serve": 70, "block": 70}},
    }
    
    libero_data = {"id": 10, "name": "Nishinoya", "position": "L", "stats": {"stamina": 100, "receive": 98, "serve": 0, "spike": 0, "block": 0}}
    
    proxies = {i: PlayerProxy(data) for i, data in players_data.items()}
    libero_proxy = PlayerProxy(libero_data)
    
    team = TeamFormation("Karasuno", proxies, libero_proxy)
    
    print("--- Initial Formation ---")
    for i in range(1, 7):
        print(f"Pos {i}: {team.get_player_in_pos(i).name} ({team.get_player_in_pos(i).role})")
    
    # MBが1番にいるので、ここでリベロ交代が起きるか確認
    team.apply_libero_substitution()
    print("\n--- After Libero Substitution ---")
    for i in range(1, 7):
        print(f"Pos {i}: {team.get_player_in_pos(i).name} ({team.get_player_in_pos(i).role})")

    # ローテーション
    print("\n--- Rotation 1 ---")
    team.rotate()
    for i in range(1, 7):
        print(f"Pos {i}: {team.get_player_in_pos(i).name} ({team.get_player_in_pos(i).role})")

    print("\n--- Rotation 2 ---")
    team.rotate()
    for i in range(1, 7):
        print(f"Pos {i}: {team.get_player_in_pos(i).name} ({team.get_player_in_pos(i).role})")

    # 試合ロジック
    print("\n--- Rally Simulation ---")
    # 対戦相手（同じチームのクローン）
    proxies_b = {i: PlayerProxy(data) for i, data in players_data.items()}
    team_b = TeamFormation("Aobajousai", proxies_b, libero_proxy)
    
    match = MatchLogic(team, team_b)
    winner = match.execute_rally(team, team_b)
    
    for log in match.logs:
        print(log)
    print(f"Winner: {winner.name}")

if __name__ == "__main__":
    test_rotation_and_libero()
