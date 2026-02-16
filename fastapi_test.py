#!/usr/bin/env python3
"""
Quick test to see if the FastAPI app can start
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

async def test_fastapi():
    """Test if FastAPI can start."""
    try:
        from app.main import app
        print("✅ FastAPI app created successfully")

        # Try to get the health endpoint
        from fastapi.testclient import TestClient
        client = TestClient(app)

        # Test health endpoint (this will fail if dependencies aren't met, but shows app structure is OK)
        try:
            response = client.get("/health")
            print(f"✅ Health endpoint responded with status {response.status_code}")
        except Exception as e:
            print(f"⚠️  Health endpoint failed (expected without Redis): {type(e).__name__}")

        return True

    except Exception as e:
        print(f"❌ FastAPI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_fastapi())
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")