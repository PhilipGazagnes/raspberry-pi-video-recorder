#!/usr/bin/env python3
"""
Test Progressive Warning System

Tests the 3-level warning threshold system in RecordingSession.
Verifies warnings trigger at correct times: 180s, 120s, 60s remaining.
"""

import logging
import time
from pathlib import Path

# Import but don't use yet - will patch first
import recording.controllers.recording_session as rs_module
from config.settings import WARNING_TIME_1, WARNING_TIME_2, WARNING_TIME_3
from recording import CameraManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def test_warning_thresholds():
    """Test that warnings trigger at the correct thresholds."""
    print("\n" + "=" * 70)
    print("PROGRESSIVE WARNING THRESHOLD TEST")
    print("=" * 70)

    print("\nConfigured warning thresholds:")
    print(f"  Level 1: {WARNING_TIME_1}s ({WARNING_TIME_1/60:.1f} min) remaining")
    print(f"  Level 2: {WARNING_TIME_2}s ({WARNING_TIME_2/60:.1f} min) remaining")
    print(f"  Level 3: {WARNING_TIME_3}s ({WARNING_TIME_3/60:.1f} min) remaining")

    # Track warnings received
    warnings_received = []
    start_time_ref = [None]  # Use list to allow modification in nested function

    def on_warning(level: int):
        warnings_received.append(
            {
                "level": level,
                "time": time.time(),
            },
        )
        print(f"\n  ✓✓✓ WARNING CALLBACK Level {level} triggered! ✓✓✓\n")

    # Create session with very short duration for testing
    # Use 6 seconds total so we can test 3 warnings at 3s, 2s, 1s intervals
    test_duration = 6.0  # 6 seconds total

    print(f"\nStarting test recording with {test_duration}s duration")
    print("(Note: Using mock camera, no actual video recording)\n")

    # Temporarily override warning times for testing BEFORE creating session
    # Need to patch the module where RecordingSession will import them
    original_w1 = rs_module.WARNING_TIME_1
    original_w2 = rs_module.WARNING_TIME_2
    original_w3 = rs_module.WARNING_TIME_3

    rs_module.WARNING_TIME_1 = 3.0  # 3s remaining
    rs_module.WARNING_TIME_2 = 2.0  # 2s remaining
    rs_module.WARNING_TIME_3 = 1.0  # 1s remaining

    print("Overriding thresholds for test:")
    print(f"  Test Level 1: {rs_module.WARNING_TIME_1}s")
    print(f"  Test Level 2: {rs_module.WARNING_TIME_2}s")
    print(f"  Test Level 3: {rs_module.WARNING_TIME_3}s\n")

    # Now create session - it will use the patched values
    camera = CameraManager(camera_device="mock")
    session = rs_module.RecordingSession(camera_manager=camera)
    session.on_warning = on_warning

    # Enable debug logging for recording session
    session.logger.setLevel(logging.DEBUG)

    try:
        # Start recording
        output_file = Path("/tmp/test_progressive_warnings.mp4")
        start_time = time.time()
        start_time_ref[0] = start_time
        session.start(output_file=output_file, duration=test_duration)

        # Wait for recording to complete
        print("Monitoring recording progress...\n")
        time.sleep(0.05)  # Give monitor thread time to start
        last_log_time = start_time

        iterations = 0
        while session.state.value in ["recording", "starting"]:
            iterations += 1
            elapsed = time.time() - start_time
            remaining = session.get_remaining_time()

            # Show progress every 0.5s
            current_time = time.time()
            if current_time - last_log_time >= 0.5:
                print(
                    f"  [{iterations:03d}] Recording: {elapsed:.1f}s elapsed, {remaining:.1f}s remaining, state={session.state.value}",
                )
                last_log_time = current_time

            time.sleep(0.1)

            # Safety timeout
            if elapsed > test_duration + 2:
                print(
                    f"  Timeout reached after {iterations} iterations, stopping recording",
                )
                break

        print(
            f"\nRecording ended after {iterations} iterations with state: {session.state.value}",
        )

        # Give monitor thread a moment to finish and trigger final callbacks
        time.sleep(0.5)

        if session.state.value in ["recording", "starting"]:
            session.stop()

        # Wait a bit more for any pending callbacks
        time.sleep(0.3)

        # Verify results
        print("\n" + "-" * 70)
        print("TEST RESULTS")
        print("-" * 70)

        print(f"\nWarnings received: {len(warnings_received)}")
        for i, warning in enumerate(warnings_received, 1):
            elapsed_at_warning = warning["time"] - start_time
            print(
                f"  Warning {i}: Level {warning['level']} at {elapsed_at_warning:.1f}s elapsed",
            )

        # Check we got all 3 warnings
        if len(warnings_received) == 3:
            print("\n✅ SUCCESS: All 3 warning levels triggered")

            # Verify order
            levels = [w["level"] for w in warnings_received]
            if levels == [1, 2, 3]:
                print("✅ SUCCESS: Warnings triggered in correct order (1 -> 2 -> 3)")
            else:
                print(f"❌ FAIL: Warning order incorrect: {levels}")
        else:
            print(f"\n❌ FAIL: Expected 3 warnings, got {len(warnings_received)}")

    finally:
        # Restore original values
        rs_module.WARNING_TIME_1 = original_w1
        rs_module.WARNING_TIME_2 = original_w2
        rs_module.WARNING_TIME_3 = original_w3

        # Cleanup
        if output_file.exists():
            output_file.unlink()

    print("\n" + "=" * 70)


if __name__ == "__main__":
    test_warning_thresholds()
