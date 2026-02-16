import asyncio
import aiosqlite

async def check_signals():
    db = await aiosqlite.connect('data/db/signalengine.db')
    db.row_factory = aiosqlite.Row
    
    # Check SKLUSDT signals
    cursor = await db.execute(
        "SELECT symbol, direction, score, timestamp FROM signals WHERE symbol LIKE '%SKL%' ORDER BY timestamp DESC LIMIT 5"
    )
    rows = await cursor.fetchall()
    print("=== SKLUSDT Signals in Database ===")
    for row in rows:
        print(f"Symbol: {row['symbol']}, Direction: {row['direction']}, Score: {row['score']:.2%}, Time: {row['timestamp']}")
    
    # Check all recent signals
    cursor = await db.execute(
        "SELECT symbol, direction, score, timestamp FROM signals ORDER BY timestamp DESC LIMIT 10"
    )
    rows = await cursor.fetchall()
    print("\n=== Recent 10 Signals (Any Symbol) ===")
    for row in rows:
        print(f"Symbol: {row['symbol']}, Direction: {row['direction']}, Score: {row['score']:.2%}, Time: {row['timestamp']}")
    
    # Count total signals
    cursor = await db.execute("SELECT COUNT(*) as count FROM signals")
    count = await cursor.fetchone()
    print(f"\n=== Total signals in database: {count['count']} ===")
    
    await db.close()

asyncio.run(check_signals())
