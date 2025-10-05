"""
Recording Session Tests

Tests for RecordingSession showing:
- Session lifecycle
- Duration tracking and limits
- Extension functionality
- Warning callbacks
- Auto-stop behavior
- State management

To run:
    pytest tests/recording/controllers/test_recording_session.py -v
"""

import time
from pathlib import Path

import pytest

from recording.constants import (
    DEFAULT_RECORDING_DURATION,
    EXTENSION_DURATION,
    MAX_RECORDING_DURATION,
    WARNING_TIME,
    RecordingState,
)
from recording.controllers.recording_session import RecordingSession

# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


@pytest.mark.unit
def test_recording_session_initialization(camera_manager):
    """Test recording session initializes correctly."""
    session = RecordingSession(camera_manager)

    assert session.state == RecordingState.IDLE
    assert session.camera is camera_manager

    session.cleanup()


# =============================================================================
# START/STOP TESTS
# =============================================================================


@pytest.mark.unit
def test_recording_session_start(recording_session, temp_video_file):
    """Test starting recording session."""
    success = recording_session.start(temp_video_file, duration=60)

    assert success is True
    assert recording_session.state == RecordingState.RECORDING

    recording_session.stop()


@pytest.mark.unit
def test_recording_session_stop(recording_session, temp_video_file):
    """Test stopping recording session."""
    recording_session.start(temp_video_file, duration=60)

    success = recording_session.stop()

    assert success is True
    assert recording_session.state == RecordingState.IDLE


@pytest.mark.unit
def test_recording_session_cannot_start_twice(recording_session, temp_video_file):
    """Test cannot start session twice."""
    recording_session.start(temp_video_file, duration=60)

    temp_file2 = temp_video_file.parent / "test2.mp4"
    success = recording_session.start(temp_file2, duration=60)

    assert success is False


@pytest.mark.unit
def test_recording_session_cannot_stop_when_idle(recording_session):
    """Test cannot stop when not recording."""
    success = recording_session.stop()

    assert success is False


# =============================================================================
# DURATION VALIDATION TESTS
# =============================================================================


@pytest.mark.unit
def test_recording_session_invalid_duration_zero(recording_session, temp_video_file):
    """Test that zero duration is rejected."""
    success = recording_session.start(temp_video_file, duration=0)

    assert success is False


@pytest.mark.unit
def test_recording_session_invalid_duration_negative(
    recording_session,
    temp_video_file,
):
    """Test that negative duration is rejected."""
    success = recording_session.start(temp_video_file, duration=-10)

    assert success is False


@pytest.mark.unit
def test_recording_session_invalid_duration_too_long(
    recording_session,
    temp_video_file,
):
    """Test that duration exceeding max is rejected."""
    success = recording_session.start(
        temp_video_file,
        duration=MAX_RECORDING_DURATION + 1,
    )

    assert success is False


@pytest.mark.unit
def test_recording_session_valid_duration_max(recording_session, temp_video_file):
    """Test that max duration is accepted."""
    success = recording_session.start(temp_video_file, duration=MAX_RECORDING_DURATION)

    assert success is True

    recording_session.stop()


# =============================================================================
# TIME TRACKING TESTS
# =============================================================================


@pytest.mark.unit
def test_recording_session_elapsed_time(temp_video_file):
    """Test elapsed time tracking."""
    from recording.controllers.camera_manager import CameraManager
    from recording.implementations.mock_capture import MockCapture

    mock = MockCapture(simulate_timing=True)
    camera = CameraManager(capture=mock)
    session = RecordingSession(camera)

    session.start(temp_video_file, duration=60)

    time.sleep(0.3)

    elapsed = session.get_elapsed_time()

    # Should be around 0.3 seconds
    assert 0.2 < elapsed < 0.4

    session.stop()
    camera.cleanup()


@pytest.mark.unit
def test_recording_session_remaining_time(temp_video_file):
    """Test remaining time calculation."""
    from recording.controllers.camera_manager import CameraManager
    from recording.implementations.mock_capture import MockCapture

    mock = MockCapture(simulate_timing=True)
    camera = CameraManager(capture=mock)
    session = RecordingSession(camera)

    session.start(temp_video_file, duration=2.0)

    time.sleep(0.5)

    remaining = session.get_remaining_time()

    # Should be around 1.5 seconds
    assert 1.3 < remaining < 1.7

    session.stop()
    camera.cleanup()


@pytest.mark.unit
def test_recording_session_elapsed_zero_when_idle(recording_session):
    """Test elapsed time is zero when not recording."""
    elapsed = recording_session.get_elapsed_time()

    assert elapsed == 0.0


@pytest.mark.unit
def test_recording_session_remaining_zero_when_idle(recording_session):
    """Test remaining time is zero when not recording."""
    remaining = recording_session.get_remaining_time()

    assert remaining == 0.0


# =============================================================================
# EXTENSION TESTS
# =============================================================================


@pytest.mark.unit
def test_recording_session_extend(recording_session, temp_video_file):
    """Test extending recording duration."""
    recording_session.start(temp_video_file, duration=DEFAULT_RECORDING_DURATION)

    initial_limit = recording_session.get_duration_limit()

    success = recording_session.extend()

    assert success is True
    assert recording_session.get_duration_limit() == initial_limit + EXTENSION_DURATION

    recording_session.stop()


@pytest.mark.unit
def test_recording_session_cannot_extend_when_idle(recording_session):
    """Test cannot extend when not recording."""
    success = recording_session.extend()

    assert success is False


@pytest.mark.unit
def test_recording_session_cannot_extend_beyond_max(recording_session, temp_video_file):
    """Test cannot extend beyond maximum duration."""
    # Start with duration that can only be extended once
    initial_duration = MAX_RECORDING_DURATION - EXTENSION_DURATION
    recording_session.start(temp_video_file, duration=initial_duration)

    # First extension should work
    success1 = recording_session.extend()
    assert success1 is True

    # Second extension should fail (would exceed max)
    success2 = recording_session.extend()
    assert success2 is False

    recording_session.stop()


@pytest.mark.unit
def test_recording_session_can_extend(recording_session, temp_video_file):
    """Test can_extend() check."""
    recording_session.start(temp_video_file, duration=DEFAULT_RECORDING_DURATION)

    # Should be able to extend
    assert recording_session.can_extend() is True

    recording_session.stop()


@pytest.mark.unit
def test_recording_session_cannot_extend_at_max(recording_session, temp_video_file):
    """Test can_extend() returns False at maximum."""
    recording_session.start(temp_video_file, duration=MAX_RECORDING_DURATION)

    # Already at max
    assert recording_session.can_extend() is False

    recording_session.stop()


# =============================================================================
# CALLBACK TESTS
# =============================================================================


@pytest.mark.unit
def test_recording_session_on_start_callback(
    camera_manager,
    temp_video_file,
    callback_tracker,
):
    """Test on_start callback is triggered."""
    session = RecordingSession(camera_manager)
    session.on_start = callback_tracker.track

    session.start(temp_video_file, duration=60)

    assert callback_tracker.was_called() is True
    assert callback_tracker.get_call_count() == 1

    session.stop()


@pytest.mark.unit
def test_recording_session_on_complete_callback(
    camera_manager,
    temp_video_file,
    callback_tracker,
):
    """Test on_complete callback is triggered."""
    session = RecordingSession(camera_manager)
    session.on_complete = callback_tracker.track

    session.start(temp_video_file, duration=60)
    session.stop()

    assert callback_tracker.was_called() is True


@pytest.mark.unit
def test_recording_session_on_extension_callback(
    camera_manager,
    temp_video_file,
    callback_tracker,
):
    """Test on_extension callback is triggered."""
    session = RecordingSession(camera_manager)
    session.on_extension = callback_tracker.track

    session.start(temp_video_file, duration=DEFAULT_RECORDING_DURATION)
    session.extend()

    assert callback_tracker.was_called() is True

    # Should receive extension count
    last_call = callback_tracker.get_last_call()
    assert last_call["args"][0] == 1  # First extension

    session.stop()


@pytest.mark.unit
def test_recording_session_on_warning_callback(callback_tracker):
    """Test on_warning callback is triggered."""
    from recording.controllers.camera_manager import CameraManager
    from recording.implementations.mock_capture import MockCapture

    mock = MockCapture(simulate_timing=True)
    camera = CameraManager(capture=mock)
    session = RecordingSession(camera)
    session.on_warning = callback_tracker.track

    temp_file = Path("/tmp/test.mp4")

    # Start with short duration that will trigger warning
    warning_duration = WARNING_TIME + 0.5  # Just over warning threshold
    session.start(temp_file, duration=warning_duration)

    # Wait for warning
    time.sleep(0.7)

    # Warning should have been triggered
    assert callback_tracker.was_called() is True

    session.stop()
    camera.cleanup()


@pytest.mark.unit
def test_recording_session_on_error_callback(
    camera_manager,
    temp_video_file,
    callback_tracker,
):
    """Test on_error callback is triggered."""
    session = RecordingSession(camera_manager)
    session.on_error = callback_tracker.track

    # Force an error by making camera fail
    camera_manager.capture.simulate_start_failure()

    # Try to start (will fail)
    success = session.start(temp_video_file, duration=60)

    assert success is False
    assert callback_tracker.was_called() is True

    # Should receive error message
    last_call = callback_tracker.get_last_call()
    assert len(last_call["args"]) > 0


# =============================================================================
# AUTO-STOP TESTS
# =============================================================================


@pytest.mark.unit
def test_recording_session_auto_stop_at_duration():
    """Test session auto-stops when duration limit reached."""
    from recording.controllers.camera_manager import CameraManager
    from recording.implementations.mock_capture import MockCapture

    mock = MockCapture(simulate_timing=True)
    camera = CameraManager(capture=mock)
    session = RecordingSession(camera)

    temp_file = Path("/tmp/test.mp4")

    # Start with very short duration
    session.start(temp_file, duration=0.5)

    assert session.state == RecordingState.RECORDING

    # Wait for auto-stop
    time.sleep(0.7)

    # Should have auto-stopped
    assert session.state == RecordingState.IDLE

    camera.cleanup()


# =============================================================================
# STATUS TESTS
# =============================================================================


@pytest.mark.unit
def test_recording_session_get_status_idle(recording_session):
    """Test get_status() when idle."""
    status = recording_session.get_status()

    assert status["state"] == RecordingState.IDLE.value
    assert status["output_file"] is None
    assert status["elapsed_time"] == 0.0
    assert status["remaining_time"] == 0.0


@pytest.mark.unit
def test_recording_session_get_status_recording(recording_session, temp_video_file):
    """Test get_status() during recording."""
    recording_session.start(temp_video_file, duration=600)

    status = recording_session.get_status()

    assert status["state"] == RecordingState.RECORDING.value
    assert status["output_file"] == str(temp_video_file)
    assert status["duration_limit"] == 600
    assert status["initial_duration"] == 600
    assert status["extension_count"] == 0
    assert status["can_extend"] is True

    recording_session.stop()


@pytest.mark.unit
def test_recording_session_get_status_after_extension(
    recording_session,
    temp_video_file,
):
    """Test get_status() after extension."""
    recording_session.start(temp_video_file, duration=DEFAULT_RECORDING_DURATION)
    recording_session.extend()

    status = recording_session.get_status()

    assert status["extension_count"] == 1
    assert status["duration_limit"] == DEFAULT_RECORDING_DURATION + EXTENSION_DURATION

    recording_session.stop()


@pytest.mark.unit
def test_recording_session_get_session_info(recording_session, temp_video_file):
    """Test get_session_info() returns formatted string."""
    recording_session.start(temp_video_file, duration=600)

    info = recording_session.get_session_info()

    assert isinstance(info, str)
    assert "State:" in info
    assert "File:" in info
    assert "Elapsed:" in info

    recording_session.stop()


@pytest.mark.unit
def test_recording_session_get_session_info_idle(recording_session):
    """Test get_session_info() when idle."""
    info = recording_session.get_session_info()

    assert "No active recording session" in info


# =============================================================================
# CLEANUP TESTS
# =============================================================================


@pytest.mark.unit
def test_recording_session_cleanup_stops_recording(camera_manager, temp_video_file):
    """Test cleanup stops active recording."""
    session = RecordingSession(camera_manager)
    session.start(temp_video_file, duration=60)

    assert session.state == RecordingState.RECORDING

    session.cleanup()

    assert session.state == RecordingState.IDLE


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


@pytest.mark.unit_integration
def test_recording_session_complete_workflow():
    """Integration test: Complete recording workflow with extensions."""
    from recording.controllers.camera_manager import CameraManager
    from recording.implementations.mock_capture import MockCapture

    mock = MockCapture(simulate_timing=True)
    camera = CameraManager(capture=mock)
    session = RecordingSession(camera)

    temp_file = Path("/tmp/test.mp4")

    # Track callbacks
    callbacks = {
        "start": False,
        "warning": False,
        "extension": 0,
        "complete": False,
    }

    def on_start():
        callbacks["start"] = True

    def on_warning():
        callbacks["warning"] = True

    def on_extension(count):
        callbacks["extension"] = count

    def on_complete():
        callbacks["complete"] = True

    session.on_start = on_start
    session.on_warning = on_warning
    session.on_extension = on_extension
    session.on_complete = on_complete

    # Start recording
    success = session.start(temp_file, duration=1.5)
    assert success is True
    assert callbacks["start"] is True

    # Wait a bit
    time.sleep(0.5)

    # Extend
    success = session.extend()
    assert success is True
    assert callbacks["extension"] == 1

    # Stop
    time.sleep(0.3)
    success = session.stop()
    assert success is True
    assert callbacks["complete"] is True

    camera.cleanup()


@pytest.mark.unit_integration
def test_recording_session_health_monitoring():
    """Integration test: Health monitoring during session."""
    from recording.controllers.camera_manager import CameraManager
    from recording.implementations.mock_capture import MockCapture

    mock = MockCapture(simulate_timing=True)
    camera = CameraManager(capture=mock)
    session = RecordingSession(camera)

    temp_file = Path("/tmp/test.mp4")

    # Start recording
    session.start(temp_file, duration=10)

    # Check health periodically
    time.sleep(0.2)
    health1 = camera.check_health()
    assert health1["is_healthy"] is True

    time.sleep(0.2)
    health2 = camera.check_health()
    assert health2["is_healthy"] is True

    # Stop
    session.stop()

    camera.cleanup()


@pytest.mark.unit_integration
def test_recording_session_multiple_extensions():
    """Test multiple extensions up to maximum."""
    from recording.controllers.camera_manager import CameraManager
    from recording.implementations.mock_capture import MockCapture

    mock = MockCapture(simulate_timing=False)
    camera = CameraManager(capture=mock)
    session = RecordingSession(camera)

    temp_file = Path("/tmp/test.mp4")

    # Start with duration that allows 3 extensions
    initial_duration = MAX_RECORDING_DURATION - (3 * EXTENSION_DURATION)
    session.start(temp_file, duration=initial_duration)

    # Extend 3 times
    assert session.extend() is True  # Extension 1
    assert session.extend() is True  # Extension 2
    assert session.extend() is True  # Extension 3

    # 4th should fail (at max)
    assert session.extend() is False

    status = session.get_status()
    assert status["extension_count"] == 3
    assert status["duration_limit"] == MAX_RECORDING_DURATION

    session.stop()
    camera.cleanup()
