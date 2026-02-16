import asyncio
import sys
sys.path.insert(0, 'C:/Projects/SignalEngine.v3')

from app.signals.on_demand_scorer import get_top_symbols

async def test():
    top = await get_top_symbols(5)
    print("\n=== Top 5 Symbols ===\n")
    for sig in top:
        print(f"Symbol: {sig['symbol']}")
        print(f"Direction: {sig['direction']}")
        print(f"Score: {sig['score']*100:.1f}%")
        print(f"Explanation: {sig['explanation'][:80]}...")
        print(f"Keys: {list(sig.keys())}")
        print("-" * 70)

asyncio.run(test())
