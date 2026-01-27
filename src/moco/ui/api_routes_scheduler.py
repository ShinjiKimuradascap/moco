"""
スケジューラー管理用のAPIルート

このモジュールはスケジューラーの起動・停止・状態確認を行うAPIを提供します
"""

from fastapi import HTTPException
from typing import Dict, Any
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# グローバルスケジューラーインスタンス
_scheduler = None
_scheduler_running = False


def start_scheduler_routes(app, approval_manager, get_orchestrator):
    """スケジューラー関連のルートをFastAPIアプリに追加"""
    
    from moco.core.scheduler import MocoScheduler
    from moco.tools.mobile import NotifyMobileTool
    
    # =============================================================================
    # ヘルパー関数
    # =============================================================================
    
    def get_scheduler():
        """スケジューラーインスタンスを取得"""
        global _scheduler
        return _scheduler
    
    async def ensure_scheduler():
        """スケジューラーが起動していることを保証"""
        global _scheduler, _scheduler_running
        if _scheduler is None or not _scheduler_running:
            # Orchestrator factory
            def orchestrator_factory(profile="default"):
                return get_orchestrator(profile)
            
            # 通知ツール
            notify_tool = NotifyMobileTool()
            
            async def scheduler_callback(task, result):
                """タスク完了時のコールバック"""
                try:
                    notification = f"""
📅 スケジュールタスク完了

タスク: {task.get('description', '')}
ID: {task.get('id')}
実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

結果:
{result[:1000]}
                    """.strip()
                    await notify_tool.execute(notification)
                    logger.info(f"Notification sent for task {task.get('id')}")
                except Exception as e:
                    logger.error(f"Failed to send notification: {e}", exc_info=True)
            
            # スケジューラーの作成と起動
            db_path = os.path.join(os.getcwd(), "tasks.db")
            _scheduler = MocoScheduler(
                orchestrator_factory=orchestrator_factory,
                interval_seconds=60,
                db_path=db_path,
                after_execute_callback=scheduler_callback
            )
            await _scheduler.start()
            _scheduler_running = True
            logger.info("Moco Scheduler started via API")
    
    # =============================================================================
    # APIルート
    # =============================================================================
    
    @app.get("/api/scheduler/status")
    async def get_scheduler_status():
        """スケジューラーの状態を取得"""
        return {
            "running": _scheduler_running,
            "has_instance": _scheduler is not None,
            "timestamp": datetime.now().isoformat()
        }
    
    @app.post("/api/scheduler/start")
    async def start_scheduler():
        """スケジューラーを起動"""
        try:
            await ensure_scheduler()
            return {
                "status": "started",
                "message": "Moco Scheduler started successfully",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/scheduler/stop")
    async def stop_scheduler():
        """スケジューラーを停止"""
        global _scheduler_running
        if _scheduler:
            try:
                await _scheduler.stop()
                _scheduler_running = False
                return {
                    "status": "stopped",
                    "message": "Moco Scheduler stopped successfully",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Failed to stop scheduler: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        else:
            return {
                "status": "not_running",
                "message": "Scheduler is not running",
                "timestamp": datetime.now().isoformat()
            }
    
    @app.post("/api/scheduler/restart")
    async def restart_scheduler():
        """スケジューラーを再起動"""
        global _scheduler_running
        # 停止
        if _scheduler:
            try:
                await _scheduler.stop()
                _scheduler_running = False
            except Exception as e:
                logger.warning(f"Error stopping scheduler for restart: {e}")
        
        # 起動
        try:
            await ensure_scheduler()
            return {
                "status": "restarted",
                "message": "Moco Scheduler restarted successfully",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to restart scheduler: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))