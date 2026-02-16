#!/usr/bin/env python3
"""
Simple startup test for SignalEngine v3
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_startup():
    """Test basic startup components."""
    print("🚀 Testing SignalEngine v3 Startup...")

    try:
        # Test config
        from app.core.config import settings
        print(f"✅ Config loaded - {len(settings.symbols)} symbols")

        # Test Redis (optional)
        try:
            from app.core.redis_pool import init_redis
            await init_redis()
            print("✅ Redis connected")
        except Exception as e:
            print(f"⚠️  Redis not available: {e}")

        # Test database
        from app.storage.database import init_db
        await init_db()
        print("✅ Database initialized")

        # Test telegram bot import
        try:
            from app.telegram.bot import start_telegram_bot, stop_telegram_bot
            print("✅ Telegram bot module loaded")
        except ImportError as e:
            print(f"❌ Telegram bot failed: {e}")

        # Test response generator import
        try:
            from app.ai.response_generator import generate_query_response
            print("✅ Response generator available")
        except Exception as e:
            print(f"⚠️  Response generator not available: {e}")

        print("\n🎯 System is ready!")
        print("\nTo start the full system:")
        print("1. Start Redis: redis-server")
        print("2. Install required packages: pip install -r requirements.txt")
        print("3. Run: python -m app")

    except Exception as e:
        print(f"❌ Startup failed: {e}")
        return False

    return True

if __name__ == "__main__":
    success = asyncio.run(test_startup())
    sys.exit(0 if success else 1)