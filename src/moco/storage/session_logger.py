"""
SessionLogger: Manages session history and conversation context.
Generic version of IncidentLogger with rolling summarization support.
"""

import sqlite3
import json
import uuid
import threading
import os
from datetime import datetime
from typing import Any, Optional, List, Dict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Gemini client for summarization
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    genai = None
    GENAI_AVAILABLE = False

# Summarization settings
DEFAULT_MAX_TOKENS = 8000

def _get_summarize_model() -> str:
    """要約用モデルを取得 (Google genai用のGeminiモデルを返す)"""
    # session_loggerはGoogle genaiクライアントを直接使用するため、
    # 常にGeminiモデルを返す必要がある
    return os.environ.get("MOCO_SUMMARIZE_MODEL", "gemini-3-flash-preview")


def _get_default_db_path() -> str:
    """デフォルトのDBパスを取得（環境変数 > cwd > プロジェクトルート探索）"""
    if os.environ.get("SESSION_DB_PATH"):
        return os.environ["SESSION_DB_PATH"]
    
    # data/sessions.db が存在するディレクトリを親方向に遡って探す
    try:
        cwd = Path.cwd()
        # カレントディレクトリまたは親ディレクトリで data/sessions.db を探す
        check_path = cwd
        for _ in range(5):
            db_file = check_path / "data" / "sessions.db"
            if db_file.exists():
                return str(db_file)
            if check_path.parent == check_path: # Root reached
                break
            check_path = check_path.parent
    except Exception:
        pass
        
    # 見つからない場合はカレントの data/sessions.db
    return str(Path.cwd() / "data" / "sessions.db")
CHARS_PER_TOKEN = 2.5  # 日本語の場合

SUMMARIZE_PROMPT = """以下の会話履歴を構造化された要約にしてください。

## 必須カテゴリ（該当するものだけ出力）

### 1. Primary Request（主要リクエスト）
- ユーザーが最終的に達成したいこと

### 2. Files and Code（ファイルとコード）
- 読み込んだファイル: パスと概要
- 編集したファイル: パスと変更内容
- 作成したファイル: パスと目的

### 3. Key Technical Concepts（技術概念）
- 議論された技術・ライブラリ・パターン

### 4. Errors and Fixes（エラーと修正）
- 発生したエラー: エラーメッセージ
- 適用した修正: 解決方法

### 5. Pending Tasks（未完了タスク）
- まだ完了していないこと

## 重要ルール
- ファイルパスは省略せず完全なパスで記載
- コードスニペットは重要な部分のみ（10行以内）
- 推測せず、会話に明示された情報のみ記載

## 会話履歴
{conversation}

## 構造化要約
"""

ROLLING_SUMMARIZE_PROMPT = """以下は「過去の要約」と「新しい会話」です。
これらを統合して、構造化された新しい要約を作成してください。

## 必須カテゴリ（該当するものだけ出力）

### 1. Primary Request（主要リクエスト）
- ユーザーが最終的に達成したいこと（更新があれば反映）

### 2. Files and Code（ファイルとコード）
- 読み込んだファイル: パスと概要
- 編集したファイル: パスと変更内容
- 作成したファイル: パスと目的

### 3. Key Technical Concepts（技術概念）
- 議論された技術・ライブラリ・パターン

### 4. Errors and Fixes（エラーと修正）
- 発生したエラー: エラーメッセージ
- 適用した修正: 解決方法

### 5. Pending Tasks（未完了タスク）
- まだ完了していないこと（完了したものは削除）

## 重要ルール
- ファイルパスは省略せず完全なパスで記載
- 新しい情報で古い情報を更新
- 完了したタスクは Pending から削除

## 過去の要約
{previous_summary}

## 新しい会話
{new_conversation}

## 統合された要約
"""


class ContextHealthMonitor:
    """コンテキストの健康状態を監視"""

    NOTICE_THRESHOLD = 4000
    WARNING_THRESHOLD = 6000
    CRITICAL_THRESHOLD = 8000

    def __init__(self, chars_per_token: float = 2.5):
        self.chars_per_token = chars_per_token

    def estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return int(len(text) / self.chars_per_token)

    def check_health(self, history: List[Dict], system_prompt: str = "") -> Dict[str, Any]:
        """コンテキストの健康状態をチェック"""
        total_chars = len(system_prompt)
        for msg in history:
            content = msg.get("content") or msg.get("parts", [""])[0]
            if isinstance(content, list):
                content = str(content)
            total_chars += len(str(content))

        # total_chars は文字数。文字数からトークン数を推定する（数値を文字列化しない）
        total_tokens = int(total_chars / self.chars_per_token) if total_chars else 0

        is_healthy = total_tokens < self.WARNING_THRESHOLD
        warning = None

        if total_tokens >= self.CRITICAL_THRESHOLD:
            warning = f"🚨 CRITICAL: コンテキストが{total_tokens}トークン。要約を推奨。"
            is_healthy = False
        elif total_tokens >= self.WARNING_THRESHOLD:
            warning = f"⚠️ WARNING: コンテキストが{total_tokens}トークン。"
        elif total_tokens >= self.NOTICE_THRESHOLD:
            warning = f"💡 NOTICE: コンテキストが{total_tokens}トークン。"

        return {
            "total_tokens": total_tokens,
            "is_healthy": is_healthy,
            "warning": warning,
            "recommend_summarize": total_tokens >= self.WARNING_THRESHOLD
        }


class SessionLogger:
    """
    Logger for persisting session history to SQLite.
    Supports rolling summarization for long sessions.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _get_default_db_path()
        self._lock = threading.RLock()
        self.context_monitor = ContextHealthMonitor()
        # Transcript directory (same parent as db)
        self.transcript_dir = Path(self.db_path).parent / "transcripts"
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self.transcript_dir.mkdir(parents=True, exist_ok=True)
            self._init_db()
        except Exception as e:
            logger.error(f"SessionLogger init failed: {e}")
    
    def get_transcript_path(self, session_id: str) -> Path:
        """Get the transcript file path for a session."""
        return self.transcript_dir / f"{session_id}.txt"
    
    def append_to_transcript(self, session_id: str, entry_type: str, content: str, agent_name: str = None):
        """Append an entry to the session transcript file.
        
        Args:
            session_id: Session ID
            entry_type: Type of entry (user, assistant, tool_call, tool_result, thinking)
            content: Content to append
            agent_name: Optional agent name
        """
        try:
            transcript_path = self.get_transcript_path(session_id)
            timestamp = datetime.now().strftime("%H:%M:%S")
            agent_prefix = f" ({agent_name})" if agent_name else ""
            
            with open(transcript_path, "a", encoding="utf-8") as f:
                if entry_type == "tool_call":
                    f.write(f"\n[{timestamp}] [Tool call]{agent_prefix} {content}\n")
                elif entry_type == "tool_result":
                    f.write(f"[Tool result]\n{content}\n")
                elif entry_type == "user":
                    f.write(f"\n{'='*60}\n[{timestamp}] USER:\n{content}\n")
                elif entry_type == "assistant":
                    f.write(f"\n[{timestamp}] ASSISTANT{agent_prefix}:\n{content}\n")
                elif entry_type == "thinking":
                    f.write(f"\n[{timestamp}] [Thinking]{agent_prefix}\n{content}\n")
                else:
                    f.write(f"\n[{timestamp}] [{entry_type}]{agent_prefix}:\n{content}\n")
        except Exception as e:
            logger.debug(f"Failed to append to transcript: {e}")

    def _get_connection(self, timeout: float = 10.0) -> sqlite3.Connection:
        """データベース接続を取得し、PRAGMAを設定する。"""
        conn = sqlite3.connect(self.db_path, timeout=timeout)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_db(self):
        """Initialize database tables."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'OPEN',
                    title TEXT,
                    profile TEXT NOT NULL DEFAULT 'default',
                    created_at TIMESTAMP NOT NULL,
                    last_updated TIMESTAMP NOT NULL,
                    metadata TEXT
                )
            """)

            # Add profile column if it doesn't exist (for backward compatibility)
            try:
                cursor.execute("ALTER TABLE sessions ADD COLUMN profile TEXT NOT NULL DEFAULT 'default'")
                conn.commit()
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    raise


            # Session Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_events (
                    event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    event_type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    content TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            # Agent conversation history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    role TEXT NOT NULL,
                    agent_id TEXT,
                    content TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            # Rolling summaries
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_summaries (
                    session_id TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    summarized_until_timestamp TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    summary_count INTEGER DEFAULT 0
                )
            """)

            # Backward compatible migration: add summary_count if missing
            try:
                cursor.execute("ALTER TABLE session_summaries ADD COLUMN summary_count INTEGER DEFAULT 0")
                conn.commit()
            except sqlite3.OperationalError as e:
                # duplicate column name -> already migrated
                if "duplicate column name" not in str(e):
                    raise

            # Todo list items
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS todos (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)

            # Indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_status ON sessions(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_session ON session_events(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_message_session ON agent_messages(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_todos_session ON todos(session_id)")

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"DB init failed: {e}")

    def create_session(self, profile: str = 'default', title: str = "New Session", **metadata) -> str:
        """Create a new session and return its ID."""
        session_id = f"SES-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                now = datetime.now().isoformat()
                metadata_json = json.dumps(metadata, ensure_ascii=False)

                cursor.execute("""
                    INSERT INTO sessions (session_id, status, title, profile, created_at, last_updated, metadata)
                    VALUES (?, 'OPEN', ?, ?, ?, ?, ?)
                """, (session_id, title, profile, now, now, metadata_json))

                conn.commit()
                conn.close()

            logger.info(f"Created session: {session_id} with profile: {profile}")
            return session_id
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return session_id

    def list_sessions(self, limit: int = 10, profile: str = None) -> List[Dict[str, Any]]:
        """List recent sessions, optionally filtered by profile."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                if profile:
                    cursor.execute("""
                        SELECT session_id, title, profile, status, created_at, last_updated
                        FROM sessions
                        WHERE profile = ?
                        ORDER BY last_updated DESC
                        LIMIT ?
                    """, (profile, limit))
                else:
                    cursor.execute("""
                        SELECT session_id, title, profile, status, created_at, last_updated
                        FROM sessions
                        ORDER BY last_updated DESC
                        LIMIT ?
                    """, (limit,))

                rows = cursor.fetchall()
                conn.close()

                return [
                    {
                        "session_id": row[0],
                        "title": row[1],
                        "profile": row[2],
                        "status": row[3],
                        "created_at": row[4],
                        "last_updated": row[5],
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def log_agent_message(
        self,
        session_id: str,
        role: str,
        content: str,
        agent_id: Optional[str] = None
    ):
        """Log an agent conversation message."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                message_id = str(uuid.uuid4())
                now = datetime.now().isoformat()

                cursor.execute("""
                    INSERT INTO agent_messages (message_id, session_id, timestamp, role, agent_id, content)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (message_id, session_id, now, role, agent_id, content))

                # Update session last_updated
                cursor.execute("""
                    UPDATE sessions SET last_updated = ? WHERE session_id = ?
                """, (now, session_id))

                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Failed to log agent message: {e}")

    def get_agent_history(
        self,
        session_id: str,
        limit: int = 20,
        format: str = "gemini",
        max_tokens: int = DEFAULT_MAX_TOKENS
    ) -> List[Dict[str, Any]]:
        """
        Get agent conversation history with optional summarization.

        Args:
            session_id: Session ID
            limit: Max messages to return
            format: "gemini" or "openai"
            max_tokens: Max tokens for context
        """
        try:
            # Get existing summary
            summary = self._get_rolling_summary(session_id)

            # Get recent messages
            messages = self._get_recent_messages(session_id, limit)

            if not messages:
                return []

            # Check context health
            health = self.context_monitor.check_health(messages)

            # 構造化サマリー自動生成（メッセージが30以上で、コンテキストが大きくなったら）
            if health["recommend_summarize"] and len(messages) > 30:
                older_messages = messages[:-20]
                self._update_rolling_summary(session_id, summary, older_messages)
                messages = messages[-20:]
                summary = self._get_rolling_summary(session_id)

            result = []

            # Add summary if exists
            if summary:
                summary_text = f"[過去の会話の要約]\n{summary}\n[要約ここまで]"
                if format == "gemini":
                    result.append({"role": "user", "parts": [summary_text]})
                else:
                    result.append({"role": "system", "content": summary_text})

            # Add recent messages
            for msg in messages:
                db_role = msg["role"]
                content = msg["content"]
                
                if format == "openai":
                    if db_role == "user":
                        result.append({"role": "user", "content": content})
                    elif db_role == "assistant":
                        # content might be text or JSON with tool_calls
                        try:
                            if content.startswith("{") and "tool_calls" in content:
                                data = json.loads(content)
                                result.append({
                                    "role": "assistant",
                                    "content": data.get("content"),
                                    "tool_calls": data.get("tool_calls")
                                })
                            else:
                                result.append({"role": "assistant", "content": content})
                        except:
                            result.append({"role": "assistant", "content": content})
                    elif db_role == "tool":
                        try:
                            data = json.loads(content)
                            if isinstance(data, dict) and "tool_call_id" in data:
                                result.append({
                                    "role": "tool",
                                    "tool_call_id": data["tool_call_id"],
                                    "content": data.get("content", "")
                                })
                            else:
                                result.append({"role": "tool", "content": content})
                        except:
                             result.append({"role": "tool", "content": content})
                    else:
                        # Fallback for other roles
                        result.append({"role": db_role, "content": content})
                else:
                    # Gemini format
                    role = "user" if db_role == "user" else ("model" if db_role == "assistant" else db_role)
                    
                    if db_role == "assistant":
                        try:
                            if content.startswith("{") and "tool_calls" in content:
                                # Tool calls in Gemini format need to be converted to FunctionCall parts
                                # For now, we just append as text or skip if complex
                                # Better to try parsing and creating parts if possible
                                data = json.loads(content)
                                parts = []
                                if data.get("content"):
                                    parts.append(data["content"])
                                # Note: converting tool_calls to Gemini parts is complex
                                # simplified: just use the text if present
                                if not parts:
                                    parts.append(content)
                                result.append({"role": role, "parts": parts})
                            else:
                                result.append({"role": role, "parts": [content]})
                        except:
                            result.append({"role": role, "parts": [content]})
                    elif db_role == "tool":
                        # Gemini doesn't accept 'tool' role directly in history.
                        # Tool results should be sent as 'user' role with function_response parts.
                        # However, perfectly reconstructing this requires the original function name.
                        # For simplicity, we skip tool results in Gemini history as the model
                        # should have already processed them in the same turn.
                        # Alternatively, include as a text summary for context.
                        try:
                            data = json.loads(content)
                            if isinstance(data, dict) and "content" in data:
                                # Include as a text note in user role for context
                                tool_id = data.get("tool_call_id", "unknown")
                                tool_content = data.get("content", "")
                                # Truncate long tool results
                                if len(tool_content) > 500:
                                    tool_content = tool_content[:500] + "...(truncated)"
                                result.append({
                                    "role": "user", 
                                    "parts": [f"[Previous tool result ({tool_id})]: {tool_content}"]
                                })
                        except:
                            # Skip malformed tool messages
                            pass
                    else:
                        result.append({"role": role, "parts": [content]})

            return result

        except Exception as e:
            logger.error(f"Failed to get agent history: {e}")
            return []

    def get_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get raw messages for a session."""
        return self._get_recent_messages(session_id, limit)

    def _get_recent_messages(self, session_id: str, limit: int) -> List[Dict[str, Any]]:
        """Get recent messages from DB.
        
        Args:
            session_id: Session ID
            limit: Number of TURNS (user messages) to retrieve, not raw message count.
                   All associated assistant/tool messages for each turn are included.
        """
        try:
            with self._lock:
                conn = self._get_connection()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # First, get the timestamps of the last N user messages (turns)
                cursor.execute("""
                    SELECT timestamp FROM agent_messages
                    WHERE session_id = ? AND role = 'user'
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (session_id, limit))
                
                user_timestamps = cursor.fetchall()
                
                if not user_timestamps:
                    conn.close()
                    return []
                
                # Get the oldest user message timestamp from our selection
                oldest_turn_timestamp = user_timestamps[-1][0]
                
                # Now get ALL messages from that timestamp onwards
                # This includes all tool calls and results for each turn
                cursor.execute("""
                    SELECT role, content, agent_id, timestamp
                    FROM agent_messages
                    WHERE session_id = ? AND timestamp >= ?
                    ORDER BY timestamp ASC
                """, (session_id, oldest_turn_timestamp))

                rows = cursor.fetchall()
                conn.close()

            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []

    def _get_rolling_summary(self, session_id: str) -> Optional[str]:
        """Get existing rolling summary."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT summary FROM session_summaries WHERE session_id = ?
                """, (session_id,))

                row = cursor.fetchone()
                conn.close()

                return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to get summary: {e}")
            return None

    def get_summary_depth(self, session_id: str) -> int:
        """Get the number of times summary has been updated (summary depth)."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT summary_count FROM session_summaries WHERE session_id = ?
                """, (session_id,))

                row = cursor.fetchone()
                conn.close()

                return row[0] if row and row[0] else 0
        except Exception as e:
            logger.error(f"Failed to get summary depth: {e}")
            return 0

    def _save_rolling_summary(self, session_id: str, summary: str):
        """Save rolling summary."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                now = datetime.now().isoformat()

                # 既存のsummary_countを取得
                cursor.execute(
                    "SELECT summary_count FROM session_summaries WHERE session_id = ?",
                    (session_id,)
                )
                row = cursor.fetchone()
                current_count = (row[0] or 0) if row else 0

                cursor.execute("""
                    INSERT OR REPLACE INTO session_summaries
                    (session_id, summary, summarized_until_timestamp, updated_at, summary_count)
                    VALUES (?, ?, ?, ?, ?)
                """, (session_id, summary, now, now, current_count + 1))

                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Failed to save summary: {e}")

    def _update_rolling_summary(
        self,
        session_id: str,
        existing_summary: Optional[str],
        messages: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Update rolling summary with new messages."""
        if not messages:
            return existing_summary

        if not GENAI_AVAILABLE:
            logger.warning("Gemini not available for summarization")
            return existing_summary

        try:
            api_key = (
                os.environ.get("GENAI_API_KEY") or
                os.environ.get("GEMINI_API_KEY") or
                os.environ.get("GOOGLE_API_KEY")
            )
            if not api_key:
                logger.warning("No API key for summarization")
                return existing_summary

            client = genai.Client(api_key=api_key)

            # Build conversation text (include tool calls)
            conversation_lines = []
            for msg in messages:
                role = msg.get("role", "assistant")
                content = msg.get("content", "")[:1000]  # 長めに取得（ツール結果含む）
                
                if role == "user":
                    conversation_lines.append(f"ユーザー: {content}")
                elif role == "tool":
                    # ツール呼び出しは [TOOL] プレフィックスで識別
                    conversation_lines.append(f"ツール: {content}")
                else:
                    conversation_lines.append(f"アシスタント: {content}")
            new_conversation = "\n".join(conversation_lines)

            # Build prompt
            if existing_summary:
                prompt = ROLLING_SUMMARIZE_PROMPT.format(
                    previous_summary=existing_summary,
                    new_conversation=new_conversation
                )
            else:
                prompt = SUMMARIZE_PROMPT.format(conversation=new_conversation)

            # Call LLM
            response = client.models.generate_content(
                model=_get_summarize_model(),
                contents=prompt
            )

            new_summary = response.text.strip() if response.text else None

            if new_summary:
                self._save_rolling_summary(session_id, new_summary)
                logger.info(f"Updated summary for session {session_id}")

            return new_summary

        except Exception as e:
            logger.error(f"Failed to update summary: {e}")
            return existing_summary

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session details."""
        try:
            with self._lock:
                conn = self._get_connection()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
                row = cursor.fetchone()
                conn.close()

                if row:
                    data = dict(row)
                    if data.get("metadata"):
                        try:
                            data["metadata"] = json.loads(data["metadata"])
                        except Exception:
                            pass
                    return data
                return None
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
            return None

    def get_session_profile(self, session_id: str) -> str:
        """Get the profile of a session."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute("SELECT profile FROM sessions WHERE session_id = ?", (session_id,))
                row = cursor.fetchone()
                conn.close()

                return row[0] if row else 'default'
        except Exception as e:
            logger.error(f"Failed to get session profile for {session_id}: {e}")
            return 'default'


    def add_event(self, session_id: str, event_type: str, source: str, content: Any) -> str:
        """Add an event to a session."""
        event_id = str(uuid.uuid4())
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                now = datetime.now().isoformat()
                content_json = json.dumps(content, ensure_ascii=False) if not isinstance(content, str) else content

                cursor.execute("""
                    INSERT INTO session_events (event_id, session_id, timestamp, event_type, source, content)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (event_id, session_id, now, event_type, source, content_json))

                cursor.execute("""
                    UPDATE sessions SET last_updated = ? WHERE session_id = ?
                """, (now, session_id))

                conn.commit()
                conn.close()

            return event_id
        except Exception as e:
            logger.error(f"Failed to add event: {e}")
            return event_id

    def get_events(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get events for a session."""
        try:
            with self._lock:
                conn = self._get_connection()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT event_id, timestamp, event_type, source, content
                    FROM session_events
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (session_id, limit))

                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return []

    def update_session_status(self, session_id: str, status: str):
        """Update session status."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                now = datetime.now().isoformat()

                cursor.execute("""
                    UPDATE sessions SET status = ?, last_updated = ?
                    WHERE session_id = ?
                """, (status, now, session_id))

                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Failed to update session status: {e}")

    def save_todos(self, session_id: str, todos: List[Dict[str, Any]]):
        """Save todo list for a session (replaces existing)."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Delete existing todos for this session
                cursor.execute("DELETE FROM todos WHERE session_id = ?", (session_id,))

                # Insert or replace todos
                now = datetime.now().isoformat()
                for todo in todos:
                    # セッション固有のIDを生成（session_id + todo_id）
                    unique_id = f"{session_id}-{todo.get('id', 'unknown')}"
                    # NOT NULL制約対策: デフォルト値を設定
                    content = todo.get("content") or "(no content)"
                    status = todo.get("status") or "pending"
                    priority = todo.get("priority") or "medium"
                    cursor.execute("""
                        INSERT OR REPLACE INTO todos (id, session_id, content, status, priority, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        unique_id,
                        session_id,
                        content,
                        status,
                        priority,
                        now,
                        now
                    ))

                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Failed to save todos: {e}")
            raise e

    def get_todos(self, session_id: str) -> List[Dict[str, Any]]:
        """Get todo list for a session."""
        try:
            with self._lock:
                conn = self._get_connection()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT id, content, status, priority
                    FROM todos
                    WHERE session_id = ?
                    ORDER BY created_at ASC
                """, (session_id,))

                rows = cursor.fetchall()
                conn.close()

                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get todos: {e}")
            return []

    def clear_summary(self, session_id: str):
        """Clear the rolling summary for a session."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute("DELETE FROM session_summaries WHERE session_id = ?", (session_id,))

                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Failed to clear summary: {e}")

    def delete_session(self, session_id: str):
        """Delete a session and all its related data."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM session_events WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM agent_messages WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM session_summaries WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM todos WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                conn.commit()
                conn.close()
            logger.info(f"Deleted session: {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            raise e

    def resolve_session_id(self, session_id_prefix: str) -> Optional[Dict[str, Any]]:
        """Resolve a session ID from a prefix (partial ID)."""
        try:
            with self._lock:
                conn = self._get_connection()
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Try exact match first
                cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id_prefix,))
                row = cursor.fetchone()
                if row:
                    conn.close()
                    return dict(row)

                # Try prefix match
                cursor.execute("SELECT * FROM sessions WHERE session_id LIKE ? LIMIT 1", (f"{session_id_prefix}%",))
                row = cursor.fetchone()
                conn.close()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to resolve session ID {session_id_prefix}: {e}")
            return None

    def update_session(self, session_id: str, title: Optional[str] = None, status: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Update session attributes."""
        try:
            with self._lock:
                conn = self._get_connection()
                cursor = conn.cursor()
                now = datetime.now().isoformat()

                updates = []
                params = []

                if title is not None:
                    updates.append("title = ?")
                    params.append(title)
                if status is not None:
                    updates.append("status = ?")
                    params.append(status)
                if metadata is not None:
                    updates.append("metadata = ?")
                    params.append(json.dumps(metadata, ensure_ascii=False))

                if not updates:
                    conn.close()
                    return

                updates.append("last_updated = ?")
                params.append(now)
                params.append(session_id)

                sql = f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = ?"
                cursor.execute(sql, params)
                conn.commit()
                conn.close()
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            raise e

    def update_session_title(self, session_id: str, title: str):
        """Update session title. (Deprecated: use update_session)"""
        self.update_session(session_id, title=title)
