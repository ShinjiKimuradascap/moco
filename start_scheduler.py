#!/usr/bin/env python3
"""
スケジューラーを起動するスクリプト
"""
import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from moco.core.scheduler import MocoScheduler

# API URL
MOCO_API_URL = "http://localhost:8000/api/chat"

async def main():
    print("=" * 60)
    print("Starting Moco Scheduler")
    print("=" * 60)
    print(f"API URL: {MOCO_API_URL}")
    print(f"Working directory: {os.getcwd()}")
    print("")
    
    # Create scheduler (API mode, no orchestrator factory needed)
    scheduler = MocoScheduler(
        orchestrator_factory=None,  # API経由なので不要
        interval_seconds=60,  # 1分ごとにチェック
        db_path=os.path.join(os.getcwd(), "tasks.db")
    )
    
    # Start scheduler
    await scheduler.start()
    
    print("Scheduler is running. Press Ctrl+C to stop.")
    print("")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)  # 1時間ごとにログ出力
            print(f"Scheduler heartbeat: {os.popen('date').read().strip()}")
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
    finally:
        await scheduler.stop()
        print("Scheduler stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
