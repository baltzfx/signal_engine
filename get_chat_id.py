"""
Get your private Telegram chat ID.

Instructions:
1. Open Telegram and search for @gaia_signal_bot
2. Send ANY message to the bot (e.g., "hello")
3. Run this script: python get_chat_id.py
4. Your private chat ID will be displayed
"""

import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def get_my_chat_id():
    """Get the chat ID of the user who messaged the bot."""
    print("=" * 60)
    print("GET YOUR TELEGRAM CHAT ID")
    print("=" * 60)
    print()
    print("📋 Instructions:")
    print("1. Open Telegram")
    print("2. Search for @gaia_signal_bot")
    print("3. Send ANY message (e.g., 'hello' or '/start')")
    print("4. Come back here and press Enter")
    print()
    input("Press Enter after you've sent a message to the bot... ")
    print()
    print("🔍 Fetching updates from Telegram...")
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            
            if response.status_code != 200:
                print(f"❌ Error: {response.text}")
                return
            
            data = response.json()
            
            if not data.get("ok"):
                print(f"❌ API Error: {data}")
                return
            
            updates = data.get("result", [])
            
            if not updates:
                print("⚠️  No messages found!")
                print("\nMake sure you:")
                print("  1. Sent a message to @gaia_signal_bot")
                print("  2. Used the correct bot")
                print("  3. Sent the message recently (within last few minutes)")
                return
            
            print(f"\n✓ Found {len(updates)} message(s)\n")
            print("=" * 60)
            print("YOUR CHAT IDs:")
            print("=" * 60)
            
            chat_ids = set()
            
            for update in updates:
                if "message" in update:
                    msg = update["message"]
                    chat = msg.get("chat", {})
                    chat_id = chat.get("id")
                    chat_type = chat.get("type", "unknown")
                    
                    if chat_id:
                        chat_ids.add((chat_id, chat_type))
                        
                        # Display details
                        username = chat.get("username", "N/A")
                        first_name = chat.get("first_name", "")
                        last_name = chat.get("last_name", "")
                        full_name = f"{first_name} {last_name}".strip() or "N/A"
                        
                        print(f"\nChat Type: {chat_type}")
                        print(f"Chat ID: {chat_id}")
                        if chat_type == "private":
                            print(f"Name: {full_name}")
                            print(f"Username: @{username}" if username != "N/A" else "Username: N/A")
                        elif chat_type in ("group", "supergroup"):
                            title = chat.get("title", "N/A")
                            print(f"Group Name: {title}")
            
            print("\n" + "=" * 60)
            print("NEXT STEPS:")
            print("=" * 60)
            
            # Find private chat ID
            private_chats = [cid for cid, ctype in chat_ids if ctype == "private"]
            
            if private_chats:
                private_id = private_chats[0]
                print(f"\n✅ Your private chat ID is: {private_id}")
                print("\n📝 Add this to your .env file:")
                print(f"\nTELEGRAM_ALLOWED_CHAT_IDS=[\"-1003497403947\",\"{private_id}\"]")
                print("\nThis will allow:")
                print("  • Signal notifications → Group (-1003497403947)")
                print(f"  • Bot queries → Your private chat ({private_id})")
                print("\n⚠️  Don't forget to restart the server after updating .env!")
            else:
                print("\n⚠️  No private chat found.")
                print("Make sure you sent a message directly to @gaia_signal_bot")
                print("(not in a group)")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(get_my_chat_id())
