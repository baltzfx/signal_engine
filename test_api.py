#!/usr/bin/env python3
"""
Test the SignalEngine API endpoints
"""

import requests

def test_health():
    """Test health endpoint"""
    try:
        r = requests.get('http://localhost:8000/health')
        print(f"Health: {r.status_code}")
        data = r.json()
        print(f"  Redis: {data.get('redis')}")
        print(f"  Symbols tracked: {data.get('symbols_tracked')}")
        return True
    except Exception as e:
        print(f"Health test failed: {e}")
        return False

def test_query():
    """Test query endpoint"""
    try:
        r = requests.get('http://localhost:8000/query/top-symbols?count=3')
        print(f"Query: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"  Query: {data.get('query')}")
            symbols = data.get('top_symbols', [])
            print(f"  Top symbols: {len(symbols)}")
            if symbols:
                for i, sym in enumerate(symbols[:3], 1):
                    print(f"    {i}. {sym['symbol']} - {sym['score']:.3f} confidence")
            ai_len = len(data.get('ai_analysis', ''))
            print(f"  AI Analysis: {ai_len} characters")
        else:
            print(f"  Error: {r.text}")
        return r.status_code == 200
    except Exception as e:
        print(f"Query test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing SignalEngine API\n")

    health_ok = test_health()
    print()

    if health_ok:
        query_ok = test_query()
    else:
        print("❌ Skipping query test - health check failed")
        query_ok = False

    print(f"\n📊 Results: {'✅ All tests passed!' if health_ok and query_ok else '❌ Some tests failed'}")