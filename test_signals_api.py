"""Test signals API endpoint."""
import httpx
import asyncio

async def test():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            # Test signals endpoint
            response = await client.get('http://localhost:8000/signals?limit=10')
            if response.status_code == 200:
                data = response.json()
                print(f"✓ /signals API working")
                print(f"  Count: {data.get('count', 0)}")
                
                if data.get('signals'):
                    print(f"\n  Latest 5 signals from API:")
                    for sig in data['signals'][:5]:
                        print(f"    {sig['symbol']:12} {sig['direction']:5} score={sig.get('score', 0):.2f} ts={sig.get('timestamp', 0)}")
                else:
                    print(f"  ⚠️ API returned 0 signals")
                
                # Check score distribution
                if data.get('signals'):
                    scores = [s.get('score', 0) for s in data['signals']]
                    print(f"\n  Score range: {min(scores):.2f} - {max(scores):.2f}")
                    high_scores = [s for s in scores if s >= 0.60]
                    print(f"  High scores (>=0.60): {len(high_scores)}/{len(scores)}")
                    
            else:
                print(f"❌ API error: {response.status_code}")
                print(f"   {response.text}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

asyncio.run(test())
