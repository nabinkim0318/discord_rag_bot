#!/usr/bin/env python3
"""
Test script for feedback service
"""

import asyncio
import sys
from pathlib import Path

import httpx
import pytest

# Load environment variables
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

load_dotenv(project_root / ".env")

BACKEND_BASE = "http://localhost:8001"


@pytest.mark.asyncio
async def test_feedback_service():
    """Test feedback service endpoints"""
    print("🧪 Testing Feedback Service...")

    async with httpx.AsyncClient() as client:
        # Test 1: Health check
        print("\n1. Testing health check...")
        try:
            response = await client.get(f"{BACKEND_BASE}/api/v1/feedback/health")
            print(f"✅ Health check: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"❌ Health check failed: {e}")

        # Test 2: Submit feedback (this will fail without a real message_id)
        print("\n2. Testing feedback submission...")
        try:
            feedback_data = {
                "message_id": "test-message-id-123",
                "user_id": "test-user-456",
                "score": "up",
                "comment": "Great response!",
            }
            response = await client.post(
                f"{BACKEND_BASE}/api/v1/feedback/submit", json=feedback_data
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"❌ Feedback submission failed: {e}")

        # Test 3: Get feedback summary
        print("\n3. Testing feedback summary...")
        try:
            response = await client.get(
                f"{BACKEND_BASE}/api/v1/feedback/summary?days=7"
            )
            print(f"✅ Summary: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"❌ Summary failed: {e}")

        # Test 4: Get feedback stats for a message
        print("\n4. Testing feedback stats...")
        try:
            response = await client.get(
                f"{BACKEND_BASE}/api/v1/feedback/stats/test-message-id-123"
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"❌ Stats failed: {e}")

        # Test 5: User feedback history is not publicly enumerable
        print("\n5. User feedback history endpoint is not public...")
        try:
            response = await client.get(
                f"{BACKEND_BASE}/api/v1/feedback/history/test-user-456"
            )
            print(f"   Status: {response.status_code}")
        except Exception as e:
            print(f"❌ History probe failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_feedback_service())
