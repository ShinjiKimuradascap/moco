import random
from typing import List, Dict, Any, Optional

class GachaEngine:
    """
    ハイキュー!! TOUCH THE DREAM クローン用ガチャエンジン
    商用グレードの整数ベースの抽選、マイレージシステム、確定枠ロジックを実装
    """

    # 1-10000 の整数ベースの閾値
    THRESHOLD_ICONIC = 300    # 3.0%
    THRESHOLD_GOLD = 1500     # 12.0%
    THRESHOLD_SILVER = 5000   # 35.0%
    # Normal は 5001-10000 (50.0%)

    # 天井（マイレージ）設定
    MILEAGE_LIMIT = 200

    def _determine_rarity(self, force_guaranteed_gold: bool = False) -> str:
        """
        単発のレアリティ抽選を行う
        """
        if force_guaranteed_gold:
            # 10連の10回目などの確定枠（Gold以上）
            # Iconic 3.0% (1-300), Gold 12.0% (301-1500)
            # 確定枠内での比率を Iconic:Gold = 3:12 (1:4) とする場合
            r = random.randint(1, 1500)
            if r <= self.THRESHOLD_ICONIC:
                return "Iconic"
            else:
                return "Gold"

        # 通常抽選
        r = random.randint(1, 10000)
        if r <= self.THRESHOLD_ICONIC:
            return "Iconic"
        elif r <= self.THRESHOLD_GOLD:
            return "Gold"
        elif r <= self.THRESHOLD_SILVER:
            return "Silver"
        else:
            return "Normal"

    def _get_iconic_detail(self) -> str:
        """
        Iconic 当選時、1/3 の確率でピックアップ対象を返す
        """
        # 300のうち100がピックアップ (1-100)
        if random.randint(1, 300) <= 100:
            return "Pickup Iconic"
        return "Standard Iconic"

    def draw_gacha(self, user_id: str, pull_count: int, times: int = 1) -> Dict[str, Any]:
        """
        ガチャを実行するメイン関数

        Args:
            user_id: ユーザー識別子
            pull_count: 現在のマイレージ (0〜199)
            times: 引く回数 (1 or 10)

        Returns:
            Dict: 抽選結果リストと更新後のマイレージ
        """
        results = []
        new_pull_count = pull_count

        for i in range(times):
            new_pull_count += 1
            is_pity = False
            rarity = "Normal"
            detail = ""

            # 1. 天井（マイレージ）判定
            if new_pull_count >= self.MILEAGE_LIMIT:
                rarity = "Iconic"
                is_pity = True
                new_pull_count = 0 # 交換消費によりリセット
            else:
                # 2. 10連確定枠判定 (最後の1枚かつ Pity でない場合)
                force_gold = (times == 10 and i == 9)
                rarity = self._determine_rarity(force_guaranteed_gold=force_gold)

            # 3. 詳細決定 (Iconicの場合)
            if rarity == "Iconic":
                detail = self._get_iconic_detail()

            # 結果を格納
            results.append({
                "rarity": rarity,
                "detail": detail if detail else rarity,
                "is_pity": is_pity
            })

            # 注意: マイレージ方式のため、通常の Iconic 排出では new_pull_count をリセットしない

        return {
            "user_id": user_id,
            "results": results,
            "new_pull_count": new_pull_count,
            "total_pulls": times
        }

if __name__ == "__main__":
    # --- 動作確認テスト ---
    engine = GachaEngine()
    test_uid = "user_456"

    print("=== Test 1: Pickup Logic (Check Iconic Details) ===")
    iconic_results = []
    for _ in range(3000): # 統計的に確認
        res = engine._determine_rarity()
        if res == "Iconic":
            iconic_results.append(engine._get_iconic_detail())
    
    pickup_count = iconic_results.count("Pickup Iconic")
    std_count = iconic_results.count("Standard Iconic")
    print(f"Iconic Hits: {len(iconic_results)}")
    print(f"  - Pickup: {pickup_count} ({pickup_count/max(1,len(iconic_results))*100:.1f}%)")
    print(f"  - Standard: {std_count} ({std_count/max(1,len(iconic_results))*100:.1f}%)")

    print("\n=== Test 2: 10-Pull Guaranteed Gold or Above ===")
    res10 = engine.draw_gacha(test_uid, pull_count=0, times=10)
    for i, r in enumerate(res10['results']):
        print(f"  [{i+1}] {r['rarity']} ({r['detail']})")
    # 最後の1枚が Gold 以上であることを目視または簡易検証
    last_rarity = res10['results'][-1]['rarity']
    print(f"Last Slot Rarity: {last_rarity} (Should be Iconic/Gold)")

    print("\n=== Test 3: Mileage System (at 199 pulls) ===")
    # 199回引いた状態で1回引く -> 天井発動
    res_pity = engine.draw_gacha(test_uid, pull_count=199, times=1)
    print(f"Result: {res_pity['results'][0]['rarity']} (is_pity: {res_pity['results'][0]['is_pity']})")
    print(f"New Mileage (should reset to 0): {res_pity['new_pull_count']}")

    print("\n=== Test 4: Mileage Persistence (Natural Iconic) ===")
    # Iconic が出てもマイレージがリセットされないことを確認
    mileage = 100
    while True:
        res = engine.draw_gacha(test_uid, pull_count=mileage, times=1)
        mileage = res['new_pull_count']
        if res['results'][0]['rarity'] == "Iconic" and not res['results'][0]['is_pity']:
            print(f"Natural Iconic Pulled! Mileage is now: {mileage} (should not be 0)")
            break
        if mileage == 0: # 万が一天井までいっちゃった場合
            break

    print("\n=== Test 5: Simulation (10,000 draws) ===")
    stats = {"Iconic": 0, "Gold": 0, "Silver": 0, "Normal": 0}
    mileage = 0
    total_draws = 10000
    for _ in range(total_draws // 10):
        batch = engine.draw_gacha(test_uid, pull_count=mileage, times=10)
        for r in batch['results']:
            stats[r['rarity']] += 1
        mileage = batch['new_pull_count']

    print(f"Total Draws: {total_draws}")
    for rarity, count in stats.items():
        percentage = (count / total_draws) * 100
        print(f"  {rarity}: {count} ({percentage:.2f}%)")

