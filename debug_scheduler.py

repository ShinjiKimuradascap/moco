#!/usr/bin/env python3
"""
デバッグ用スケジューラー
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from moco.storage.scheduled_task_store import ScheduledTaskStore
import httpx

# API URL
MOCO_API_URL = "http://localhost:8000/api/chat"

async def main():
    print("=" * 60)
    print("Debug Scheduler")
    print("=" * 60)
    print(f"API URL: {MOCO_API_URL}")
    print(f"Working directory: {os.getcwd()}")
    print("")
    
    # Create store
    store = ScheduledTaskStore(db_path=os.path.join(os.getcwd(), "tasks.db"))
    
    # Loop forever
    while True:
        now = datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{now_str}] Checking for due tasks...")
        
        # Get enabled tasks
        tasks = store.get_enabled_tasks()
        print(f"Total enabled tasks: {len(tasks)}")
        for t in tasks:
            print(f"  - {t['id']}: {t['description'][:30]} | next_run: {t['next_run']} | enabled: {t['enabled']}")
        
        # Get due tasks
        due_tasks = store.get_due_tasks()
        print(f"Due tasks: {len(due_tasks)}")
        
        for task in due_tasks:
            task_id = task['id']
            description = task['description']
            profile = task.get('profile', 'default')
            working_dir = task.get('working_dir') or os.getcwd()
            
            print(f"\nExecuting task: {task_id}")
            print(f"Description: {description}")
            print(f"Profile: {profile}")
            print(f"Working dir: {working_dir}")
            
            try:
                payload = {
                    "message": description,
                    "session_id": None,
                    "profile": profile,
                    "working_directory": working_dir
                }
                
                print(f"Sending request to API...")
                async with httpx.AsyncClient(timeout=300.0) as client:
                    response = await client.post(MOCO_API_URL, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("response", "")
                    artifacts = data.get("artifacts", [])
                    print(f"✅ Task completed successfully")
                    print(f"Result: {result[:200]}...")
                    if artifacts:
                        print(f"Generated {len(artifacts)} artifacts")
                    
                    # Mark task as completed
                    store.complete_task(task_id)
                    print(f"Task {task_id} marked as completed")
                else:
                    print(f"❌ Task failed with status {response.status_code}")
                    print(f"Response: {response.text[:200]}")
                    store.complete_task(task_id)
                
            except Exception as e:
                print(f"❌ Error executing task {task_id}: {e}")
                import traceback
                traceback.print_exc()
                store.complete_task(task_id)
        
        print("\nWaiting 30 seconds...")
        await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
