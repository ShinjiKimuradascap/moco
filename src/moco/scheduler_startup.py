#!/usr/bin/env python3
"""
Moco スケジューラー起動スクリプト

このスクリプトは以下を行います：
1. MocoScheduler を起動
2. 定期的にスケジュールタスクをチェックして実行
3. 実行結果をモバイル（WhatsApp等）に通知

使用方法:
    python -m moco.scheduler_startup
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from moco.core.scheduler import MocoScheduler
from moco.core.orchestrator import Orchestrator
from moco.tools.mobile import send_file_to_mobile, NotifyMobileTool

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SchedulerCallbackHandler:
    """スケジューラーのコールバックを処理"""
    
    def __init__(self):
        self.notify_tool = NotifyMobileTool()
    
    async def handle_task_completion(self, task: dict, result: str):
        """
        タスク完了時のコールバック
        WhatsApp等に結果を通知する
        """
        task_id = task.get('id')
        description = task.get('description', '')
        
        logger.info(f"Task {task_id} completed, sending notification...")
        
        # 結果を通知
        notification_text = f"""
📅 スケジュールタスク完了

タスク: {description}
ID: {task_id}
実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

結果:
{result[:1000]}  # 最初の1000文字だけ
        """.strip()
        
        try:
            # モバイルに通知
            await self.notify_tool.execute(notification_text)
            logger.info(f"Notification sent for task {task_id}")
        except Exception as e:
            logger.error(f"Failed to send notification for task {task_id}: {e}", exc_info=True)


async def main():
    """メイン関数"""
    logger.info("=" * 60)
    logger.info("Moco Scheduler Startup")
    logger.info("=" * 60)
    
    # 作業ディレクトリの確認
    working_dir = os.environ.get("MOCO_WORKING_DIRECTORY")
    if not working_dir:
        working_dir = os.getcwd()
    logger.info(f"Working directory: {working_dir}")
    
    # Orchestrator factory
    def orchestrator_factory(profile="default"):
        """Orchestratorを生成するファクトリー関数"""
        return Orchestrator(profile=profile)
    
    # コールバックハンドラー
    callback_handler = SchedulerCallbackHandler()
    
    # スケジューラーの初期化
    db_path = os.path.join(working_dir, "tasks.db")
    logger.info(f"Task database: {db_path}")
    
    scheduler = MocoScheduler(
        orchestrator_factory=orchestrator_factory,
        interval_seconds=60,  # 1分ごとにチェック
        db_path=db_path,
        after_execute_callback=callback_handler.handle_task_completion
    )
    
    # スケジューラーを開始
    logger.info("Starting scheduler...")
    await scheduler.start()
    
    # 継続実行（Ctrl+Cで停止）
    try:
        logger.info("Scheduler is running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(3600)  # 1時間ごとにログ出力
            logger.info(f"Scheduler heartbeat: {datetime.now().isoformat()}")
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
    finally:
        await scheduler.stop()
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
