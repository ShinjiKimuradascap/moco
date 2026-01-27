import random

class MatchEngine:
    def __init__(self, team_a, team_b):
        self.team_a = team_a
        self.team_b = team_b
        self.score_a = 0
        self.score_b = 0
        self.state = "SERVE" # SERVE, RECEIVE, TOSS, ATTACK, DIG, RESULT

    def calculate_success(self, attacker_val, defender_val, modifier=1.0):
        """成功判定式 (基本)"""
        base_rate = (attacker_val / max(1, defender_val)) * modifier
        chance = random.uniform(0.9, 1.1) * base_rate
        return chance > 1.0

    def simulate_point(self):
        """1ポイントの決着までをシミュレート"""
        # 簡易ステートマシン実装
        print("--- Point Start ---")
        # 1. Serve
        if self.calculate_success(80, 70): # 例: サーバーのステータス vs レシーバー
            print("Serve Success")
            # 2. Receive
            if self.calculate_success(75, 80):
                print("Receive Good")
                # 3. Toss & Attack
                if self.calculate_success(90, 85): # スパイク成功判定
                    print("Spike Kill! Point A")
                    self.score_a += 1
                else:
                    print("Blocked! Point B")
                    self.score_b += 1
            else:
                print("Ace! Point A")
                self.score_a += 1
        else:
            print("Serve Error. Point B")
            self.score_b += 1

if __name__ == "__main__":
    engine = MatchEngine("Karasuno", "Aoba Josai")
    for _ in range(5):
        engine.simulate_point()
    print(f"Final Score: {engine.score_a} - {engine.score_b}")
