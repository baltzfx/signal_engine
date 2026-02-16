"""
Send a test message to verify the Telegram bot is responding to chats.
"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


async def send_message_to_bot(message_text: str):
    """Simulate sending a message to the bot and getting updates."""
    base_url = f"https://api.telegram.org/bot{BOT_TOKEN}"
    
    # First, send a message to the chat (simulating user message)
    print(f"📤 Sending test message to chat...")
    send_url = f"{base_url}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message_text,
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(send_url, json=payload)
        if response.status_code == 200:
            print(f"✓ Message sent successfully")
            result = response.json()
            print(f"  Message ID: {result['result']['message_id']}")
        else:
            print(f"❌ Failed to send message: {response.text}")
            return
    
    # Wait a moment for the bot to process
    print("\n⏳ Waiting 3 seconds for bot to process...")
    await asyncio.sleep(3)
    
    # Get recent updates to see if bot responded
    print("\n📥 Checking for bot response...")
    updates_url = f"{base_url}/getUpdates"
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(updates_url, params={"limit": 10})
        if response.status_code == 200:
            updates = response.json()
            if updates["result"]:
                print(f"\n✓ Found {len(updates['result'])} recent updates:")
                for update in updates["result"][-5:]:  # Show last 5
                    if "message" in update:
                        msg = update["message"]
                        text = msg.get("text", "")
                        from_user = msg.get("from", {}).get("username", "unknown")
                        print(f"  - From: {from_user}")
                        print(f"    Text: {text[:100]}")
                        print()
            else:
                print("⚠️  No recent updates found")
        else:
            print(f"❌ Failed to get updates: {response.text}")
    
    # Check bot info
    print("\n🤖 Bot Information:")
    me_url = f"{base_url}/getMe"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(me_url)
        if response.status_code == 200:
            bot_info = response.json()["result"]
            print(f"  Name: {bot_info.get('first_name', '')}")
            print(f"  Username: @{bot_info.get('username', '')}")
            print(f"  ID: {bot_info.get('id', '')}")
            print(f"  Can read all messages: {bot_info.get('can_read_all_group_messages', False)}")


async def main():
    print("=" * 60)
    print("TELEGRAM BOT CHAT TEST")
    print("=" * 60)
    print()
    
    test_message = "🧪 Test message - What's the top symbols for futures now?"
    await send_message_to_bot(test_message)
    
    print("\n" + "=" * 60)
    print("IMPORTANT:")
    print("=" * 60)
    print("If the bot is NOT responding to your messages, it could be:")
    print("1. The bot polling is not running (check server logs)")
    print("2. The bot doesn't have permission to read group messages")
    print("3. The bot needs /start command first in private chat")
    print("\nTry these:")
    print("1. Open Telegram and send '/start' to the bot")
    print("2. Make sure the bot is added to the group (if using group chat)")
    print("3. Type: @gaia_signal_bot and mention it in messages")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
