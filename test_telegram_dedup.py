"""
Test script to verify Telegram deduplication logic works correctly.
Creates multiple test signals and sends them to verify they all go through.
"""

import asyncio
import time
from app.storage.database import init_db
from app.telegram.bot import _hash_signal, _try_send
from app.core.config import settings

async def test_dedup():
    """Test that unique signals get unique hashes."""
    print("🧪 Testing Telegram Deduplication Logic\n")
    
    # Create test signals - same symbol, same direction, different times
    base_time = time.time()
    
    signals = [
        {
            "symbol": "TESTUSDT",
            "direction": "long",
            "score": 0.55,
            "timestamp": base_time,
            "entry_price": 100.0,
            "tp_price": 105.0,
            "sl_price": 98.0,
        },
        {
            "symbol": "TESTUSDT",
            "direction": "long",
            "score": 0.58,  # Different score
            "timestamp": base_time + 300,  # 5 minutes later
            "entry_price": 101.0,
            "tp_price": 106.0,
            "sl_price": 99.0,
        },
        {
            "symbol": "TESTUSDT",
            "direction": "long",
            "score": 0.62,  # Different score again
            "timestamp": base_time + 600,  # 10 minutes later
            "entry_price": 102.0,
            "tp_price": 107.0,
            "sl_price": 100.0,
        },
    ]
    
    # Test hash uniqueness
    print("📊 Testing Hash Uniqueness:")
    hashes = []
    for i, sig in enumerate(signals, 1):
        sig_hash = _hash_signal(sig)
        hashes.append(sig_hash)
        print(f"  Signal {i}: {sig_hash[:8]}... (score={sig['score']}, time offset={sig['timestamp']-base_time}s)")
    
    unique_hashes = len(set(hashes))
    print(f"\n✅ Result: {unique_hashes}/{len(signals)} unique hashes")
    
    if unique_hashes == len(signals):
        print("✅ PASS: All signals have unique hashes (dedup working correctly!)\n")
    else:
        print("❌ FAIL: Duplicate hashes detected (dedup too aggressive!)\n")
        return
    
    # Test actual sending
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        print("⚠️  Telegram not configured - skipping send test")
        return
    
    print("📤 Testing Telegram Sending:")
    print("   (Will send 3 test signals to your Telegram chat)\n")
    
    for i, sig in enumerate(signals, 1):
        print(f"  Sending test signal {i}...")
        success = await _try_send(sig)
        if success:
            print(f"  ✅ Signal {i} sent successfully")
        else:
            print(f"  ❌ Signal {i} failed to send")
        await asyncio.sleep(1)  # Rate limiting
    
    print("\n✅ Test complete! Check your Telegram chat for 3 test signals.")


if __name__ == "__main__":
    asyncio.run(test_dedup())
