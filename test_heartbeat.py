#!/usr/bin/env python3
"""
Quick test to verify heartbeat functionality.

Tests:
1. Heartbeat file is created
2. Heartbeat contains expected fields
3. Heartbeat timestamp updates
"""

import json
import sys
import time
from pathlib import Path

# /tmp is intentional - matches production heartbeat location
HEARTBEAT_FILE = Path("/tmp/recorder_heartbeat.json")  # noqa: S108


def test_heartbeat():
    """Test heartbeat file creation and updates."""
    print("Testing heartbeat functionality...")
    print(f"Monitoring: {HEARTBEAT_FILE}")
    print()

    # Wait for first heartbeat
    print("Waiting for first heartbeat (max 5 seconds)...")
    for _ in range(50):
        if HEARTBEAT_FILE.exists():
            break
        time.sleep(0.1)
    else:
        print("❌ FAILED: No heartbeat file created within 5 seconds")
        return False

    # Read first heartbeat
    heartbeat1 = json.loads(HEARTBEAT_FILE.read_text())
    print("✅ Heartbeat file created!")
    print(f"   State: {heartbeat1.get('state')}")
    print(f"   PID: {heartbeat1.get('pid')}")
    print(f"   Timestamp: {heartbeat1.get('timestamp')}")
    print()

    # Verify required fields
    required_fields = [
        "timestamp",
        "uptime_seconds",
        "state",
        "recording_active",
        "upload_queue_size",
        "currently_uploading",
        "pid",
    ]
    missing = [f for f in required_fields if f not in heartbeat1]
    if missing:
        print(f"❌ FAILED: Missing fields: {missing}")
        return False
    print("✅ All required fields present!")
    print()

    # Wait for update (heartbeat should update every 1 second)
    print("Waiting for heartbeat update (max 3 seconds)...")
    time.sleep(2)

    heartbeat2 = json.loads(HEARTBEAT_FILE.read_text())
    if heartbeat2["timestamp"] == heartbeat1["timestamp"]:
        print("❌ FAILED: Heartbeat not updating")
        return False

    print("✅ Heartbeat is updating!")
    print(f"   Old timestamp: {heartbeat1['timestamp']}")
    print(f"   New timestamp: {heartbeat2['timestamp']}")
    print()

    print("=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = test_heartbeat()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        sys.exit(1)
