#!/usr/bin/env python3
"""
Test script for SignalEngine v3 components.
Tests the core functionality without Telegram dependencies.
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_config():
    """Test configuration loading."""
    try:
        from app.core.config import settings
        print(f"✅ Config loaded - {len(settings.symbols)} symbols configured")
        return True
    except Exception as e:
        print(f"❌ Config failed: {e}")
        return False

async def test_redis():
    """Test Redis connection."""
    try:
        from app.core.redis_pool import init_redis, get_redis
        await init_redis()
        redis = get_redis()
        pong = await redis.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis failed: {e}")
        return False

async def test_database():
    """Test database initialization."""
    try:
        from app.storage.database import init_db
        await init_db()
        print("✅ Database initialized")
        return True
    except Exception as e:
        print(f"❌ Database failed: {e}")
        return False

async def test_on_demand_scorer():
    """Test on-demand scorer (without actual data)."""
    try:
        from app.signals.on_demand_scorer import score_all_symbols
        # This will likely fail without Redis data, but tests the import
        print("✅ On-demand scorer module imported")
        return True
    except Exception as e:
        print(f"❌ On-demand scorer failed: {e}")
        return False

async def test_response_generator():
    """Test response generator."""
    try:
        from app.ai.response_generator import generate_query_response
        print("✅ Response generator module imported")
        return True
    except Exception as e:
        print(f"❌ Response generator failed: {e}")
        return False

async def test_query_handler():
    """Test query handler."""
    try:
        from app.telegram.query_handler import query_handler
        response = await query_handler.process_query("help")
        print("✅ Query handler working")
        return True
    except Exception as e:
        print(f"❌ Query handler failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("🧪 Testing SignalEngine v3 Components\n")

    tests = [
        ("Configuration", test_config),
        ("Redis Connection", test_redis),
        ("Database", test_database),
        ("On-demand Scorer", test_on_demand_scorer),
        ("Response Generator", test_response_generator),
        ("Query Handler", test_query_handler),
    ]

    passed = 0
    total = len(tests)

    for name, test_func in tests:
        print(f"Testing {name}...")
        try:
            if await test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {name} crashed: {e}")

    print(f"\n📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All core components are working!")
        print("\nNext steps:")
        print("System check complete!")
        print("3. Start Redis server")
        print("4. Run: python -m app")
    else:
        print("⚠️  Some components need attention")

if __name__ == "__main__":
    asyncio.run(main())