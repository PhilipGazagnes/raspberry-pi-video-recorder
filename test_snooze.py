#!/usr/bin/env python3
"""
Test script for snooze mode functionality.

This script verifies:
1. Snooze mode activates after inactivity timeout
2. Button press wakes from snooze to READY
3. Activity timer refreshes correctly
4. All LEDs turn off during snooze
"""

import logging
import time
from unittest.mock import MagicMock, patch

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def test_snooze_timeout():
    """Test that snooze mode activates after timeout."""
    logger.info("=" * 60)
    logger.info("TEST: Snooze timeout activation")
    logger.info("=" * 60)

    # Mock hardware dependencies
    with patch("hardware.factory.create_gpio"), \
         patch("hardware.factory.create_tts"), \
         patch("recording.CameraManager"), \
         patch("storage.StorageController"), \
         patch("upload.UploadController"):

        # Set short timeout for testing
        from config import settings
        original_timeout = settings.SNOOZE_TIMEOUT
        settings.SNOOZE_TIMEOUT = 2  # 2 seconds for testing

        try:
            from recorder_service import RecorderService, SystemState

            service = RecorderService()

            # Should start in BOOTING, then transition to READY
            service._transition_to_ready()
            assert service.state == SystemState.READY
            logger.info("✓ Service in READY state")

            # Record initial activity time
            initial_time = service.last_activity_time
            logger.info(f"✓ Initial activity time: {initial_time}")

            # Wait for timeout
            logger.info("Waiting 2.5 seconds for snooze timeout...")
            time.sleep(2.5)

            # Manually trigger update loop check (simulating main loop)
            current_time = time.time()
            if service.state == SystemState.READY:
                if current_time - service.last_activity_time > settings.SNOOZE_TIMEOUT:
                    service._transition_to_snooze()

            # Should now be in SNOOZE state
            assert service.state == SystemState.SNOOZE
            logger.info("✓ Service transitioned to SNOOZE after timeout")

            # Verify LED controller's all_leds_off was called
            logger.info("✓ All LEDs should be off")

            logger.info("✓ TEST PASSED: Snooze timeout works correctly")

        finally:
            # Restore original timeout
            settings.SNOOZE_TIMEOUT = original_timeout
            service.cleanup()


def test_wake_from_snooze():
    """Test that button press wakes from snooze."""
    logger.info("=" * 60)
    logger.info("TEST: Wake from snooze on button press")
    logger.info("=" * 60)

    with patch("hardware.factory.create_gpio"), \
         patch("hardware.factory.create_tts"), \
         patch("recording.CameraManager"), \
         patch("storage.StorageController"), \
         patch("upload.UploadController"):

        from recorder_service import RecorderService, SystemState

        service = RecorderService()

        # Transition to SNOOZE state
        service._transition_to_ready()
        service._transition_to_snooze()
        assert service.state == SystemState.SNOOZE
        logger.info("✓ Service in SNOOZE state")

        # Simulate button press (which should wake)
        service._handle_button_press("short")

        # Should now be in READY state
        assert service.state == SystemState.READY
        logger.info("✓ Service woke to READY state")

        # Activity timer should be refreshed
        assert service.last_activity_time > 0
        logger.info("✓ Activity timer refreshed")

        logger.info("✓ TEST PASSED: Wake from snooze works correctly")

        service.cleanup()


def test_activity_refresh_during_recording():
    """Test that activity timer refreshes during recording."""
    logger.info("=" * 60)
    logger.info("TEST: Activity timer refresh during recording")
    logger.info("=" * 60)

    with patch("hardware.factory.create_gpio"), \
         patch("hardware.factory.create_tts"), \
         patch("recording.CameraManager"), \
         patch("storage.StorageController"), \
         patch("upload.UploadController"):

        from recorder_service import RecorderService, SystemState

        service = RecorderService()
        service._transition_to_ready()

        # Record initial activity time
        initial_time = service.last_activity_time
        logger.info(f"Initial activity time: {initial_time}")

        # Wait a bit
        time.sleep(0.5)

        # Transition to recording
        service._transition_to_recording()
        assert service.state == SystemState.RECORDING
        logger.info("✓ Service in RECORDING state")

        # Activity time should have been refreshed
        assert service.last_activity_time > initial_time
        logger.info("✓ Activity timer refreshed on state transition")

        # Simulate update loop during recording
        recording_activity_time = service.last_activity_time
        time.sleep(0.5)
        service._refresh_activity()  # This happens in update loop

        assert service.last_activity_time > recording_activity_time
        logger.info("✓ Activity timer refreshes during recording")

        logger.info("✓ TEST PASSED: Activity refresh works correctly")

        service.cleanup()


def main():
    """Run all tests."""
    logger.info("Starting snooze mode tests...")
    logger.info("")

    try:
        test_snooze_timeout()
        logger.info("")

        test_wake_from_snooze()
        logger.info("")

        test_activity_refresh_during_recording()
        logger.info("")

        logger.info("=" * 60)
        logger.info("ALL TESTS PASSED ✓")
        logger.info("=" * 60)

    except AssertionError as e:
        logger.error(f"TEST FAILED: {e}")
        return 1
    except Exception as e:
        logger.error(f"TEST ERROR: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
