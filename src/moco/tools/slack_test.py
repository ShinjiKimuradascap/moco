import slack_sdk
import os
from datetime import datetime, timedelta

def get_slack_messages_last_day():
    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        print("Error: SLACK_BOT_TOKEN not found")
        return
        
    client = slack_sdk.WebClient(token=token)
    
    # チャンネル一覧を取得
    channels = []
    cursor = None
    while True:
        response = client.conversations_list(cursor=cursor, types="public_channel,private_channel")
        channels.extend(response["channels"])
        cursor = response.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break
            
    # 過去24時間のメッセージを取得
    oldest = (datetime.now() - timedelta(days=1)).timestamp()
    
    all_messages = []
    for channel in channels:
        if not channel["is_member"]:
            continue
            
        print(f"Fetching messages from #{channel['name']}")
        try:
            response = client.conversations_history(channel=channel["id"], oldest=oldest)
            messages = response["messages"]
            for msg in messages:
                if "text" in msg and msg.get("type") == "message":
                    all_messages.append({
                        "channel": channel["name"],
                        "user": msg.get("user"),
                        "text": msg["text"],
                        "ts": msg["ts"]
                    })
        except Exception as e:
            print(f"Error fetching #{channel['name']}: {e}")
            
    return all_messages

if __name__ == "__main__":
    messages = get_slack_messages_last_day()
    if messages:
        for m in messages:
            print(f"[{m['channel']}] {m['text']}")
