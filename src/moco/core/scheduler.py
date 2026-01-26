import asyncio
import logging
from datetime import datetime
from typing import Optional

from ..storage.scheduled_task_store import ScheduledTaskStore
from .orchestrator import Orchestrator

logger = logging.getLogger(__name__)

class MocoScheduler:
    """
    Moco スケジュール実行エンジン。
    定期的にデータベースをチェックし、実行時刻が到来したタスクを Orchestrator に渡す。
    """

    def __init__(
        self,
        orchestrator_factory,
        interval_seconds: int = 60,
        db_path: Optional[str] = None,
        after_execute_callback = None
    ):
        """
        Args:
            orchestrator_factory: Orchestratorのインスタンスを生成する呼び出し可能オブジェクト、
                                 または既存のOrchestrator。
                                 タスクごとに異なるprofileを適用するため、factoryが望ましい。
            interval_seconds: チェック間隔（秒）
            db_path: タスクDBのパス
            after_execute_callback: タスク完了時に呼ばれるコールバック (task_dict, result_text)
        """
        self.orchestrator_factory = orchestrator_factory
        self.interval_seconds = interval_seconds
        self.store = ScheduledTaskStore(db_path=db_path)
        self.after_execute_callback = after_execute_callback
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """スケジューラーをバックグラウンドで開始する"""
        if self._running:
            logger.warning("Scheduler is already running.")
            return

        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Moco Scheduler started.")

    async def stop(self):
        """スケジューラーを停止する"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Moco Scheduler stopped.")

    async def _loop(self):
        """メイン実行ループ"""
        while self._running:
            try:
                await self._check_and_execute_tasks()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
            
            await asyncio.sleep(self.interval_seconds)

    async def _check_and_execute_tasks(self):
        """期限が来たタスクをチェックして実行する"""
        due_tasks = self.store.get_due_tasks()
        if not due_tasks:
            return

        logger.info(f"Found {len(due_tasks)} due tasks.")

        for task in due_tasks:
            task_id = task['id']
            description = task['description']
            profile = task.get('profile', 'default')
            
            logger.info(f"Executing task {task_id}: {description} (profile: {profile})")
            
            try:
                # Orchestratorの準備
                if callable(self.orchestrator_factory):
                    orchestrator = self.orchestrator_factory(profile=profile)
                else:
                    orchestrator = self.orchestrator_factory
                
                # タスクの実行
                session_id = f"scheduled_{task_id}_{datetime.now().strftime('%Y%m%d%H%M')}"
                
                result = await orchestrator.run(description, session_id=session_id)
                logger.debug(f"Task {task_id} result: {result[:100]}...")
                
                # 完了通知と次回予定の更新
                self.store.complete_task(task_id)
                logger.info(f"Task {task_id} completed successfully.")

                # コールバックの実行（モバイル等への通知）
                if self.after_execute_callback:
                    try:
                        if asyncio.iscoroutinefunction(self.after_execute_callback):
                            await self.after_execute_callback(task, result)
                        else:
                            self.after_execute_callback(task, result)
                    except Exception as callback_err:
                        logger.error(f"Error in scheduler callback: {callback_err}")
                
            except Exception as e:
                logger.error(f"Failed to execute task {task_id}: {e}", exc_info=True)
                self.store.complete_task(task_id)

if __name__ == "__main__":
    # 簡単な動作確認用のモック
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        from .orchestrator import Orchestrator
        
        def factory(profile="default"):
            return Orchestrator(profile=profile)
            
        scheduler = MocoScheduler(factory, interval_seconds=10)
        
        # テストタスクの追加
        store = ScheduledTaskStore()
        store.add_task("test_ping", "現在時刻を教えて", "*/1 * * * *") # 毎分
        
        await scheduler.start()
        await asyncio.sleep(65) # 1サイクル待機
        await scheduler.stop()

    asyncio.run(main())
