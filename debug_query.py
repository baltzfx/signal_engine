#!/usr/bin/env python3
"""
Debug script for SignalEngine query issues.
"""
import asyncio
import sys
import os
sys.path.append('.')

from app.core.redis_pool import init_redis
from app.signals.on_demand_scorer import score_all_symbols, get_top_symbols
from app.ai.response_generator import generate_query_response

async def main():
    print("=== SignalEngine Debug ===")

    # Initialize Redis
    await init_redis()

    try:
        print("1. Testing score_all_symbols...")
        results = await score_all_symbols()
        print(f"   Total symbols scored: {len(results)}")

        if results:
            results.sort(key=lambda x: x['score'], reverse=True)
            print("   Top 5 symbols:")
            for i, symbol in enumerate(results[:5]):
                print(f"     {i+1}. {symbol['symbol']}: {symbol['score']:.3f} ({symbol['direction']})")
        else:
            print("   No symbols scored!")
            return

        print("\n2. Testing get_top_symbols...")
        top_symbols = await get_top_symbols(3)
        print(f"   Top symbols returned: {len(top_symbols)}")

        if top_symbols:
            print("   Top symbols:")
            for symbol in top_symbols:
                print(f"     {symbol['symbol']}: {symbol['score']:.3f}")

            print("\n3. Testing response generator...")
            try:
                response = await generate_query_response("Show me top 3 symbols", top_symbols)
                print(f"   Response: {len(response)} chars")
                print(f"   Preview: {response[:200]}...")
            except Exception as e:
                print(f"   Response error: {e}")
        else:
            print("   No top symbols returned!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())