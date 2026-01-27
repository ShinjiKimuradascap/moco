#!/usr/bin/env python3
"""
スケジュールタスクのテストスクリプト
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from moco.tools.scheduler import ScheduleTaskTool

async def main():
    print("Testing ScheduleTaskTool...")
    tool = ScheduleTaskTool()
    
    # Schedule a task to run every minute
    result = await tool.execute(
        description="現在時刻を教えて",
        cron="*/1 * * * *",
        task_id="test_schedule_python",
        profile="default"
    )
    
    print(result)
    return result

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if "✅" in result else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
