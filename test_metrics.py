#!/usr/bin/env python3
"""
Quick test to verify metrics exporter functionality.

Tests:
1. Metrics exporter starts successfully
2. /metrics endpoint returns valid Prometheus metrics
3. Required metrics are present
"""

import sys
import time
import urllib.request
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import METRICS_PORT


def test_metrics():
    """Test metrics exporter endpoint."""
    print("Testing metrics exporter...")
    print(f"Metrics endpoint: http://localhost:{METRICS_PORT}/metrics")
    print()

    # Wait for metrics server to start
    print("Waiting for metrics server to start (max 5 seconds)...")
    for _ in range(50):
        try:
            response = urllib.request.urlopen(
                f"http://localhost:{METRICS_PORT}/metrics",
                timeout=1,
            )
            break
        except (urllib.error.URLError, ConnectionRefusedError):
            time.sleep(0.1)
    else:
        print("❌ FAILED: Metrics server not responding within 5 seconds")
        return False

    # Read metrics
    metrics_text = response.read().decode("utf-8")
    print("✅ Metrics endpoint responding!")
    print()

    # Verify required metrics are present
    required_metrics = [
        "recorder_up",
        "recorder_heartbeat_age_seconds",
        "recorder_state",
        "recorder_recording_active",
        "recorder_upload_queue_size",
        "recorder_uptime_seconds",
        "recorder_disk_free_bytes",
        "recorder_disk_usage_ratio",
        "recorder_videos_total",
        "recorder_upload_success_rate",
    ]

    missing = [m for m in required_metrics if m not in metrics_text]
    if missing:
        print(f"❌ FAILED: Missing metrics: {missing}")
        return False

    print("✅ All required metrics present!")
    print()

    # Show sample metrics
    print("Sample metrics:")
    print("-" * 60)
    for line in metrics_text.split("\n")[:15]:
        if line.strip():
            print(f"  {line}")
    print("  ...")
    print("-" * 60)
    print()

    print("=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = test_metrics()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
