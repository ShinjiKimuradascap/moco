# Contributing to moco

moco への貢献に興味を持っていただきありがとうございます！🎉

このドキュメントでは、moco プロジェクトに貢献するためのガイドラインを説明します。

## 📋 目次

- [行動規範](#行動規範)
- [貢献の方法](#貢献の方法)
- [開発環境のセットアップ](#開発環境のセットアップ)
- [コーディング規約](#コーディング規約)
- [テストの実行](#テストの実行)
- [コミットメッセージの規約](#コミットメッセージの規約)
- [プルリクエストのガイドライン](#プルリクエストのガイドライン)
- [イシューの報告](#イシューの報告)
- [質問・サポート](#質問サポート)

---

## 行動規範

このプロジェクトは [Contributor Covenant](https://www.contributor-covenant.org/) の行動規範を採用しています。プロジェクトに参加することで、この規範を遵守することに同意したものとみなされます。

### 私たちの約束

- 誰もが参加しやすい、オープンで歓迎的な環境を維持します
- 異なる意見や経験を尊重します
- 建設的なフィードバックを心がけます
- コミュニティにとって最善のことに焦点を当てます

### 許容されない行動

- 攻撃的なコメントや個人攻撃
- ハラスメント（公的・私的を問わず）
- 他者の個人情報の無断公開
- その他、専門的な場にふさわしくない行為

問題が発生した場合は、プロジェクトメンテナーに報告してください。

---

## 貢献の方法

moco への貢献方法は様々です：

| 貢献の種類 | 説明 |
|-----------|------|
| 🐛 バグ報告 | 問題を発見したら Issue を作成 |
| 💡 機能提案 | 新機能のアイデアを Issue で提案 |
| 📖 ドキュメント | README、ガイド、API ドキュメントの改善 |
| 🔧 コード | バグ修正、新機能の実装 |
| 🧪 テスト | テストカバレッジの向上 |
| 🌐 翻訳 | ドキュメントの多言語化 |
| 💬 コミュニティ | 質問への回答、議論への参加 |

---

## 開発環境のセットアップ

### 必要条件

- Python 3.10 以上
- Git
- (推奨) [uv](https://github.com/astral-sh/uv) または pip

### セットアップ手順

#### 1. リポジトリをフォーク & クローン

```bash
# GitHub でリポジトリをフォーク後
git clone https://github.com/YOUR_USERNAME/moco-agent.git
cd moco-agent
```

#### 2. 開発用依存関係のインストール

```bash
# uv を使用する場合（推奨）
uv venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
uv pip install -e ".[dev,docs]"

# pip を使用する場合
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,docs]"
```

#### 3. 環境変数の設定

```bash
cp .env.example .env
# .env ファイルを編集して API キーを設定
```

```env
# 必須（いずれか1つ以上）
GEMINI_API_KEY=your-gemini-api-key
OPENAI_API_KEY=your-openai-api-key
OPENROUTER_API_KEY=your-openrouter-api-key

# オプション
MOCO_DEFAULT_PROVIDER=gemini
MOCO_LOG_LEVEL=DEBUG
```

#### 4. セットアップの確認

```bash
# CLI が動作することを確認
moco --help

# テストが通ることを確認
pytest
```

### IDE 設定

#### VS Code

推奨拡張機能:
- Python (Microsoft)
- Ruff
- Mypy Type Checker

`.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": ".venv/bin/python",
    "python.analysis.typeCheckingMode": "basic",
    "[python]": {
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.codeActionsOnSave": {
            "source.fixAll.ruff": "explicit",
            "source.organizeImports.ruff": "explicit"
        }
    }
}
```

#### PyCharm

1. File → Settings → Project → Python Interpreter で仮想環境を選択
2. File → Settings → Tools → File Watchers で Ruff を設定

---

## コーディング規約

### フォーマッター・リンター

このプロジェクトでは [Ruff](https://docs.astral.sh/ruff/) を使用しています。

```bash
# フォーマット
ruff format .

# リント
ruff check .

# リント（自動修正）
ruff check --fix .
```

### 型チェック

[mypy](https://mypy-lang.org/) で型チェックを行います。

```bash
mypy moco
```

### コーディングスタイル

#### 基本ルール

- **行の長さ**: 100 文字以内
- **インデント**: スペース 4 つ
- **クォート**: ダブルクォート `"` を優先
- **末尾カンマ**: 複数行の場合は必須

#### 型ヒント

すべての公開関数・メソッドに型ヒントを付けてください。

```python
# ✅ Good
def process_message(
    message: str,
    max_tokens: int = 1000,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """メッセージを処理して結果を返す。"""
    ...

# ❌ Bad
def process_message(message, max_tokens=1000, temperature=0.7):
    ...
```

#### Docstring

Google スタイルの docstring を使用してください。

```python
def calculate_similarity(
    query: str,
    documents: list[str],
    threshold: float = 0.5,
) -> list[tuple[int, float]]:
    """
    クエリと文書群の類似度を計算する。

    Args:
        query: 検索クエリ文字列。
        documents: 検索対象の文書リスト。
        threshold: 類似度の閾値（0.0〜1.0）。
            この値以上の類似度を持つ文書のみ返す。

    Returns:
        (文書インデックス, 類似度) のタプルのリスト。
        類似度の降順でソートされている。

    Raises:
        ValueError: threshold が 0.0〜1.0 の範囲外の場合。

    Examples:
        >>> docs = ["Python is great", "Java is good", "Python rocks"]
        >>> calculate_similarity("Python programming", docs)
        [(0, 0.85), (2, 0.78)]
    """
    ...
```

#### インポート順序

Ruff が自動で整理しますが、基本的な順序は：

```python
# 1. 標準ライブラリ
import os
import sys
from pathlib import Path

# 2. サードパーティ
import numpy as np
from pydantic import BaseModel

# 3. ローカル
from moco.core import Orchestrator
from moco.tools import read_file
```

#### 命名規則

| 種類 | 規則 | 例 |
|------|------|-----|
| モジュール | snake_case | `context_compressor.py` |
| クラス | PascalCase | `ContextCompressor` |
| 関数・メソッド | snake_case | `compress_context()` |
| 変数 | snake_case | `max_tokens` |
| 定数 | UPPER_SNAKE_CASE | `DEFAULT_MAX_TOKENS` |
| プライベート | 先頭に `_` | `_internal_method()` |

---

## テストの実行

### 全テストの実行

```bash
pytest
```

### オプション付き実行

```bash
# 詳細出力
pytest -v

# カバレッジレポート付き
pytest --cov=moco --cov-report=html

# 特定のテストファイル
pytest tests/test_orchestrator.py

# 特定のテスト関数
pytest tests/test_orchestrator.py::test_basic_conversation

# 失敗したテストのみ再実行
pytest --lf

# 並列実行（pytest-xdist が必要）
pytest -n auto
```

### テストの書き方

```python
# tests/test_example.py
import pytest
from moco.core import Orchestrator


class TestOrchestrator:
    """Orchestrator のテスト。"""

    @pytest.fixture
    def orchestrator(self):
        """テスト用の Orchestrator インスタンス。"""
        return Orchestrator(provider="openrouter")

    def test_basic_message(self, orchestrator):
        """基本的なメッセージ処理のテスト。"""
        response = orchestrator.run("Hello")
        assert response is not None
        assert isinstance(response, str)

    @pytest.mark.asyncio
    async def test_async_operation(self, orchestrator):
        """非同期処理のテスト。"""
        result = await orchestrator.run_async("Hello")
        assert result is not None

    @pytest.mark.parametrize("input,expected", [
        ("hello", "HELLO"),
        ("world", "WORLD"),
    ])
    def test_parametrized(self, input, expected):
        """パラメータ化テスト。"""
        assert input.upper() == expected
```

### カバレッジ目標

- **全体**: 80% 以上
- **コアモジュール**: 90% 以上
- **新規コード**: 100%（可能な限り）

---

## コミットメッセージの規約

[Conventional Commits](https://www.conventionalcommits.org/) に従います。

### フォーマット

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type（必須）

| Type | 説明 |
|------|------|
| `feat` | 新機能 |
| `fix` | バグ修正 |
| `docs` | ドキュメントのみの変更 |
| `style` | コードの意味に影響しない変更（フォーマット等） |
| `refactor` | バグ修正でも機能追加でもないコード変更 |
| `perf` | パフォーマンス改善 |
| `test` | テストの追加・修正 |
| `build` | ビルドシステムや依存関係の変更 |
| `ci` | CI 設定の変更 |
| `chore` | その他の変更 |

### Scope（任意）

変更の影響範囲を示します：

- `core` - コアモジュール
- `tools` - ツール
- `cli` - CLI
- `docs` - ドキュメント
- `profiles` - プロファイル

### 例

```bash
# 新機能
feat(core): add streaming response support

# バグ修正
fix(tools): handle empty file in read_file

# ドキュメント
docs: update installation guide

# 破壊的変更（! を付ける）
feat(core)!: change Orchestrator constructor signature

BREAKING CHANGE: `provider` argument is now required.
```

### コミットのベストプラクティス

1. **小さく、論理的な単位でコミット**
2. **1つのコミットで1つのことを行う**
3. **動作する状態でコミット**（ビルドが通る状態）
4. **WIP コミットは squash してからプッシュ**

---

## プルリクエストのガイドライン

### PR を作成する前に

1. [ ] 最新の `main` ブランチからブランチを作成
2. [ ] 関連する Issue がある場合はリンク
3. [ ] テストを追加・更新
4. [ ] ドキュメントを更新（必要な場合）
5. [ ] `ruff format .` と `ruff check .` を実行
6. [ ] `mypy moco` を実行
7. [ ] `pytest` が通ることを確認

### ブランチ命名規則

```
<type>/<issue-number>-<short-description>
```

例:
- `feat/123-add-streaming`
- `fix/456-handle-empty-response`
- `docs/789-update-readme`

### PR テンプレート

```markdown
## 概要
<!-- この PR で何を行うか -->

## 関連 Issue
<!-- Fixes #123 または Closes #456 -->

## 変更内容
<!-- 主な変更点をリストで -->
- 
- 

## テスト
<!-- どのようにテストしたか -->
- [ ] 単体テストを追加
- [ ] 手動テストを実施

## スクリーンショット
<!-- UI の変更がある場合 -->

## チェックリスト
- [ ] コードが規約に従っている
- [ ] テストが通る
- [ ] ドキュメントを更新した（必要な場合）
- [ ] CHANGELOG.md を更新した（必要な場合）
```

### レビュープロセス

1. **自動チェック**: CI が通ることを確認
2. **コードレビュー**: メンテナーがレビュー
3. **修正**: フィードバックに対応
4. **承認**: 1 名以上の承認が必要
5. **マージ**: Squash and merge を推奨

### マージ後

- ローカルブランチを削除
- Issue を閉じる（自動で閉じない場合）

---

## イシューの報告

### バグ報告

バグを報告する際は、以下の情報を含めてください：

```markdown
## 環境
- OS: macOS 14.0 / Ubuntu 22.04 / Windows 11
- Python: 3.11.0
- moco バージョン: 0.1.0

## 再現手順
1. `moco run --profile sre` を実行
2. "check server status" と入力
3. エラーが発生

## 期待する動作
サーバーの状態が表示される

## 実際の動作
以下のエラーが発生:
```
Traceback (most recent call last):
  ...
```

## 追加情報
- 設定ファイル（機密情報を除く）
- ログ出力
```

### 機能リクエスト

```markdown
## 概要
<!-- 提案する機能の概要 -->

## 動機
<!-- なぜこの機能が必要か -->

## 提案する解決策
<!-- どのように実装するか -->

## 代替案
<!-- 検討した他の方法 -->

## 追加情報
<!-- 参考リンク、スクリーンショット等 -->
```

### ラベル

| ラベル | 説明 |
|--------|------|
| `bug` | バグ報告 |
| `enhancement` | 機能リクエスト |
| `documentation` | ドキュメント関連 |
| `good first issue` | 初心者向け |
| `help wanted` | 助けが必要 |
| `question` | 質問 |
| `wontfix` | 対応しない |
| `duplicate` | 重複 |

---

## 質問・サポート

- **一般的な質問**: [GitHub Discussions](https://github.com/moco-ai/moco/discussions)
- **バグ報告・機能リクエスト**: [GitHub Issues](https://github.com/moco-ai/moco/issues)
- **セキュリティの問題**: SECURITY.md を参照

---

## 謝辞

moco に貢献してくださるすべての方に感謝します！

貢献者は [Contributors](https://github.com/moco-ai/moco/graphs/contributors) ページで確認できます。
