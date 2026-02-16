"""
Test script to verify Telegram integration is working.

Tests:
1. Configuration validation
2. Bot token validity
3. Message sending capability
4. Signal queue integration
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.signals.engine import get_signal_queue


async def test_telegram_config():
    """Test 1: Check if Telegram is properly configured."""
    print("=" * 60)
    print("TEST 1: Configuration Check")
    print("=" * 60)
    
    if not settings.telegram_bot_token:
        print("❌ FAIL: TELEGRAM_BOT_TOKEN not configured")
        return False
    
    print(f"✓ Bot Token: {settings.telegram_bot_token[:10]}..." )
    
    if not settings.telegram_chat_id:
        print("❌ FAIL: TELEGRAM_CHAT_ID not configured")
        return False
    
    print(f"✓ Chat ID: {settings.telegram_chat_id}")
    print(f"✓ Allowed Chat IDs: {settings.telegram_allowed_chat_ids}")
    print(f"✓ Rate Limit: {settings.telegram_rate_limit} msg/sec")
    
    return True


async def test_telegram_connection():
    """Test 2: Verify bot can connect to Telegram API."""
    print("\n" + "=" * 60)
    print("TEST 2: Telegram API Connection")
    print("=" * 60)
    
    try:
        from telegram import Update
        from telegram.ext import Application
        print("✓ python-telegram-bot library installed")
    except ImportError:
        print("❌ FAIL: python-telegram-bot not installed")
        print("   Install with: pip install python-telegram-bot")
        return False
    
    try:
        import httpx
        print("✓ httpx library installed")
    except ImportError:
        print("❌ FAIL: httpx not installed")
        print("   Install with: pip install httpx")
        return False
    
    # Test bot token validity
    try:
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getMe"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                bot_info = resp.json()
                print(f"✓ Bot connection successful!")
                print(f"  Bot name: {bot_info['result']['username']}")
                print(f"  Bot ID: {bot_info['result']['id']}")
                return True
            else:
                print(f"❌ FAIL: Invalid bot token (HTTP {resp.status_code})")
                print(f"   Response: {resp.text[:200]}")
                return False
    except Exception as e:
        print(f"❌ FAIL: Connection error: {e}")
        return False


async def test_send_message():
    """Test 3: Send a test message."""
    print("\n" + "=" * 60)
    print("TEST 3: Send Test Message")
    print("=" * 60)
    
    try:
        import httpx
        
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        payload = {
            "chat_id": settings.telegram_chat_id,
            "text": "🧪 <b>SignalEngine Test Message</b>\n\nTelegram integration is working correctly!\n\nTimestamp: " + str(asyncio.get_event_loop().time()),
            "parse_mode": "HTML",
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                print("✓ Test message sent successfully!")
                print("  Check your Telegram chat to confirm.")
                return True
            else:
                print(f"❌ FAIL: Could not send message (HTTP {resp.status_code})")
                print(f"   Response: {resp.text[:200]}")
                return False
    except Exception as e:
        print(f"❌ FAIL: Error sending message: {e}")
        return False


async def test_signal_queue():
    """Test 4: Verify signal queue integration."""
    print("\n" + "=" * 60)
    print("TEST 4: Signal Queue Integration")
    print("=" * 60)
    
    try:
        sq = get_signal_queue()
        print(f"✓ Signal queue created (max size: {sq.maxsize})")
        print(f"  Current size: {sq.qsize()}")
        
        # Test enqueue
        test_signal = {
            "symbol": "TESTUSDT",
            "direction": "long",
            "score": 0.75,
            "timestamp": asyncio.get_event_loop().time(),
            "trigger_events": ["test_event"],
        }
        
        sq.put_nowait(test_signal)
        print(f"✓ Test signal added to queue")
        print(f"  Queue size after add: {sq.qsize()}")
        
        # Dequeue it to clean up
        retrieved = sq.get_nowait()
        print(f"✓ Test signal retrieved from queue")
        print(f"  Signal: {retrieved['symbol']} {retrieved['direction']}")
        
        return True
    except Exception as e:
        print(f"❌ FAIL: Signal queue error: {e}")
        return False


async def test_bot_worker():
    """Test 5: Check if bot worker can start."""
    print("\n" + "=" * 60)
    print("TEST 5: Bot Worker Start")
    print("=" * 60)
    
    try:
        from app.telegram.bot import start_telegram_bot, start_telegram_worker
        
        print("✓ Bot functions imported successfully")
        print("\nℹ️  Note: Actual bot start requires running server")
        print("   Bot will auto-start when you run: python -m app")
        
        return True
    except Exception as e:
        print(f"❌ FAIL: Could not import bot: {e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TELEGRAM INTEGRATION TEST SUITE")
    print("=" * 60)
    print()
    
    results = []
    
    # Run tests
    results.append(("Configuration", await test_telegram_config()))
    results.append(("API Connection", await test_telegram_connection()))
    results.append(("Send Message", await test_send_message()))
    results.append(("Signal Queue", await test_signal_queue()))
    results.append(("Bot Worker", await test_bot_worker()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed! Telegram integration is ready.")
        print("\nNext steps:")
        print("1. Start the server: python -m app")
        print("2. Send a message to your bot on Telegram")
        print("3. Try a command like /start or /help")
        print("4. Signals will be sent automatically when generated")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
    
    return passed_count == total_count


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
