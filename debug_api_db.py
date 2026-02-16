"""Debug API and database."""
import httpx
import asyncio
import sqlite3

async def test_api():
    print("=" * 60)
    print("API TEST")
    print("=" * 60)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get('http://localhost:8000/signals?limit=10')
            if response.status_code == 200:
                data = response.json()
                print(f"✓ API Status: {response.status_code}")
                print(f"  Count: {data.get('count', 0)}")
                print(f"  Signals array length: {len(data.get('signals', []))}")
                
                if data.get('signals'):
                    print("\n  Signals returned:")
                    for sig in data['signals'][:5]:
                        print(f"    {sig}")
                else:
                    print("\n  ⚠️ API returned empty signals array")
            else:
                print(f"❌ API Status: {response.status_code}")
                print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ API Error: {e}")
        import traceback
        traceback.print_exc()

def test_db():
    print("\n" + "=" * 60)
    print("DATABASE TEST")
    print("=" * 60)
    try:
        conn = sqlite3.connect('data/db/signalengine.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM signals')
        total = cursor.fetchone()[0]
        print(f"Total signals in DB: {total}")
        
        cursor.execute('SELECT COUNT(*) FROM signals WHERE score >= 0.50')
        high = cursor.fetchone()[0]
        print(f"Signals with score >= 0.50: {high}")
        
        cursor.execute('SELECT symbol, direction, score FROM signals ORDER BY timestamp DESC LIMIT 5')
        print("\nLatest 5 signals in DB:")
        for row in cursor.fetchall():
            print(f"  {row}")
        
        conn.close()
    except Exception as e:
        print(f"❌ Database Error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    await test_api()
    test_db()

asyncio.run(main())
