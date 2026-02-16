#!/usr/bin/env python3
"""
Check which signals are in the database but might not have been sent to Telegram.
This helps identify signals that were dropped due to queue limits or other issues.
"""

import sqlite3
from datetime import datetime

def check_unsent_signals():
    """Check signals in database and show potential send failures."""
    conn = sqlite3.connect("data/db/signalengine.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all signals ordered by timestamp
    cursor.execute("""
        SELECT 
            id,
            symbol,
            direction,
            score,
            timestamp,
            created_at
        FROM signals
        ORDER BY timestamp DESC
        LIMIT 100
    """)
    
    signals = cursor.fetchall()
    total = len(signals)
    
    print(f"\n📊 Recent Signals Analysis ({total} signals)")
    print("=" * 80)
    
    # Group by symbol to show distribution
    symbol_counts = {}
    for sig in signals:
        symbol = sig['symbol']
        symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
    
    print(f"\n📈 Signals by Symbol:")
    for symbol, count in sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {symbol:15s} : {count:3d} signals")
    
    # Show recent signals
    print(f"\n🕒 Recent 20 Signals:")
    print("-" * 80)
    print(f"{'Time':<20} {'Symbol':<12} {'Dir':<6} {'Score':<7} {'ID':<5}")
    print("-" * 80)
    
    for sig in signals[:20]:
        dt = datetime.fromtimestamp(sig['timestamp'])
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        score = f"{sig['score']*100:.1f}%"
        direction = sig['direction'].upper()
        
        print(f"{time_str:<20} {sig['symbol']:<12} {direction:<6} {score:<7} {sig['id']:<5}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("💡 Tip: Check backend logs for 'Signal queue full' messages")
    print("💡 Restart backend to apply queue size increase (500 → 10000)")
    print()

if __name__ == "__main__":
    check_unsent_signals()
