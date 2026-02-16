"""
Debug script to check which signals are in database but not sent to Telegram.
Compares database signals with Telegram send hashes.
"""

import asyncio
from app.storage.database import init_db, get_signals
from app.core.config import settings
import hashlib

def hash_signal(signal: dict) -> str:
    """Same hash logic as telegram bot."""
    key = f"{signal.get('symbol')}:{signal.get('direction')}:{signal.get('timestamp')}:{signal.get('score')}"
    return hashlib.md5(key.encode()).hexdigest()

async def main():
    print("🔍 Checking Telegram Send Status\n")
    
    await init_db()
    
    # Get recent signals
    signals = await get_signals(limit=50)
    
    if not signals:
        print("⚠️  No signals found in database")
        return
    
    print(f"📊 Found {len(signals)} signals in database\n")
    
    # Group by symbol to find duplicates
    by_symbol = {}
    for sig in signals:
        symbol = sig['symbol']
        if symbol not in by_symbol:
            by_symbol[symbol] = []
        by_symbol[symbol].append(sig)
    
    # Check for symbols with multiple signals
    print("📈 Signals per symbol:")
    for symbol, sigs in sorted(by_symbol.items(), key=lambda x: len(x[1]), reverse=True):
        if len(sigs) > 1:
            print(f"  {symbol}: {len(sigs)} signals")
            for sig in sigs:
                direction = sig['direction']
                score = sig['score']
                timestamp = sig['timestamp']
                from datetime import datetime
                time_str = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
                sig_hash = hash_signal(sig)
                print(f"    - {direction:5s} {score:.2f} @ {time_str} | hash: {sig_hash[:8]}...")
    
    # Show recent 10 signals
    print("\n📋 Recent 10 signals:")
    for i, sig in enumerate(signals[:10], 1):
        sig_hash = hash_signal(sig)
        from datetime import datetime
        time_str = datetime.fromtimestamp(sig['timestamp']).strftime('%m-%d %H:%M:%S')
        print(f"{i:2d}. {sig['symbol']:12s} {sig['direction']:5s} {sig['score']:.2f} @ {time_str} | {sig_hash[:8]}...")
    
    print("\n💡 Each signal should have a unique hash based on:")
    print("   - Symbol")
    print("   - Direction")
    print("   - Exact timestamp")
    print("   - Score")
    print("\n✅ If hashes are unique, deduplication is working correctly")

if __name__ == "__main__":
    asyncio.run(main())
