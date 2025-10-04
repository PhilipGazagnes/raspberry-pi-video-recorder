"""
Mock Capture Tests

Tests for MockCapture implementation showing:
- Capture lifecycle
- State management
- File creation
- Timing simulation
- Test helper methods

To run:
    pytest tests/recording/implementations/test_mock_capture.py -v
"""

import time
import pytest
from pathlib import Path

from recording.implementations.mock_capture import MockCapture
from recording.interfaces.video_capture_interface import CaptureError


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================

@pytest.mark.unit
def test_mock_capture_initialization():
    """Test mock capture initializes correctly."""
    capture = MockCapture(simulate_timing=False)

    assert capture.is_available() is True
    assert capture.is_capturing() is False

    capture.cleanup()


@pytest.mark.unit
def test_mock_capture_initialization_with_timing():
    """Test mock capture with timing simulation."""
    capture = MockCapture(simulate_timing=True)

    assert capture.simulate_timing is True
    assert capture.is_available() is True

    capture.cleanup()


# =============================================================================
# BASIC CAPTURE TESTS
# =============================================================================

@pytest.mark.unit
def test_mock_capture_start_stop(mock_capture_fast, temp_video_file):
    """Test basic start and stop capture."""
    # Start capture
    success = mock_capture_fast.start_capture(temp_video_file)

    assert success is True
    assert mock_capture_fast.is_capturing() is True
    assert mock_capture_fast.get_output_file() == temp_video_file

    # Stop capture
    success = mock_capture_fast.stop_capture()

    assert success is True
    assert mock_capture_fast.is_capturing() is False
    assert temp_video_file.exists()


@pytest.mark.unit
def test_mock_capture_creates_file(mock_capture_fast, temp_video_file):
    """Test that capture creates output file."""
    mock_capture_fast.start_capture(temp_video_file)
    mock_capture_fast.stop_capture()

    # File should exist
    assert temp_video_file.exists()

    # File should have some content
    assert temp_video_file.stat().st_size > 0


@pytest.mark.unit
def test_mock_capture_cannot_start_twice(mock_capture_fast, temp_video_file):
    """Test that capture cannot be started while already capturing."""
    mock_capture_fast.start_capture(temp_video_file)

    # Try to start again
    temp_file2 = temp_video_file.parent / "test2.mp4"
    success = mock_capture_fast.start_capture(temp_file2)

    assert success is False


@pytest.mark.unit
def test_mock_capture_stop_when_not_capturing(mock_capture_fast):
    """Test stop when not capturing returns False."""
    success = mock_capture_fast.stop_capture()

    assert success is False


# =============================================================================
# DURATION TRACKING TESTS
# =============================================================================

@pytest.mark.unit
def test_mock_capture_duration_tracking_fast(mock_capture_fast, temp_video_file):
    """Test duration with fast mode (no simulation)."""
    mock_capture_fast.start_capture(temp_video_file, duration=10)

    # In fast mode, duration returns target immediately
    duration = mock_capture_fast.get_capture_duration()
    assert duration == 10.0

    mock_capture_fast.stop_capture()


@pytest.mark.unit
def test_mock_capture_duration_tracking_realistic(mock_capture_realistic, temp_video_file):
    """Test duration with realistic timing."""
    mock_capture_realistic.start_capture(temp_video_file, duration=10)

    # Wait a bit
    time.sleep(0.5)

    # Duration should be realistic
    duration = mock_capture_realistic.get_capture_duration()
    assert 0.4 < duration < 0.6  # Around 0.5 seconds

    mock_capture_realistic.stop_capture()


@pytest.mark.unit
def test_mock_capture_auto_stop_after_duration(mock_capture_realistic, temp_video_file):
    """Test that capture auto-stops after duration in realistic mode."""
    # Start with short duration
    mock_capture_realistic.start_capture(temp_video_file, duration=0.5)

    assert mock_capture_realistic.is_capturing() is True

    # Wait for auto-stop
    time.sleep(0.7)

    # Should have auto-stopped
    assert mock_capture_realistic.is_capturing() is False


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================

@pytest.mark.unit
def test_mock_capture_health_check_idle(mock_capture_fast):
    """Test health check when not capturing."""
    health = mock_capture_fast.check_health()

    assert health['is_healthy'] is False  # Should be False when not capturing
    assert "not running" in health['error_message'].lower()


@pytest.mark.unit
def test_mock_capture_health_check_running(mock_capture_fast, temp_video_file):
    """Test health check during capture."""
    mock_capture_fast.start_capture(temp_video_file, duration=10)

    health = mock_capture_fast.check_health()

    assert health['is_healthy'] is True
    assert health['error_message'] is None
    assert health['fps'] == 30.0

    mock_capture_fast.stop_capture()


@pytest.mark.unit
def test_mock_capture_health_simulated_frames(mock_capture_realistic, temp_video_file):
    """Test that health check shows simulated frame count."""
    mock_capture_realistic.start_capture(temp_video_file, duration=10)

    time.sleep(0.2)

    health = mock_capture_realistic.check_health()

    # Should have captured some frames
    assert health['frames_captured'] > 0

    mock_capture_realistic.stop_capture()


# =============================================================================
# ERROR SIMULATION TESTS
# =============================================================================

@pytest.mark.unit
def test_mock_capture_simulate_start_failure(temp_video_file):
    """Test simulating start failure for error testing."""
    capture = MockCapture(simulate_timing=False)

    # Configure to fail on start
    capture.simulate_start_failure()

    # Should raise error
    with pytest.raises(CaptureError):
        capture.start_capture(temp_video_file)

    capture.cleanup()


@pytest.mark.unit
def test_mock_capture_simulate_crash_during(mock_capture_realistic, temp_video_file):
    """Test simulating crash during capture."""
    # Configure to crash after 0.2 seconds
    mock_capture_realistic.simulate_crash_during_capture(after_seconds=0.2)

    mock_capture_realistic.start_capture(temp_video_file, duration=10)

    # Wait for crash
    time.sleep(0.3)

    # Health should show error
    health = mock_capture_realistic.check_health()
    assert health['is_healthy'] is False
    assert "crash" in health['error_message'].lower()


@pytest.mark.unit
def test_mock_capture_reset_test_config():
    """Test resetting test configuration."""
    capture = MockCapture(simulate_timing=False)

    # Configure failures
    capture.simulate_start_failure()
    capture.simulate_crash_during_capture(after_seconds=1.0)

    # Reset
    capture.reset_test_config()

    # Should work normally now
    temp_file = Path("/tmp/test.mp4")
    success = capture.start_capture(temp_file)
    assert success is True

    capture.stop_capture()
    capture.cleanup()


# =============================================================================
# HELPER METHOD TESTS
# =============================================================================

@pytest.mark.unit
def test_mock_capture_get_simulated_frames(mock_capture_realistic, temp_video_file):
    """Test getting simulated frame count."""
    mock_capture_realistic.start_capture(temp_video_file, duration=10)

    time.sleep(0.2)

    frames = mock_capture_realistic.get_simulated_frames()

    # Should have some frames
    assert frames > 0

    mock_capture_realistic.stop_capture()


# =============================================================================
# CLEANUP TESTS
# =============================================================================

@pytest.mark.unit
def test_mock_capture_cleanup_stops_capture(mock_capture_fast, temp_video_file):
    """Test that cleanup stops active capture."""
    mock_capture_fast.start_capture(temp_video_file)

    assert mock_capture_fast.is_capturing() is True

    mock_capture_fast.cleanup()

    assert mock_capture_fast.is_capturing() is False


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

@pytest.mark.unit_integration
def test_mock_capture_complete_workflow(mock_capture_realistic, temp_video_file):
    """Integration test: Complete capture workflow."""
    # Start
    mock_capture_realistic.start_capture(temp_video_file, duration=1.0)

    assert mock_capture_realistic.is_capturing() is True

    # Check health during
    time.sleep(0.3)
    health = mock_capture_realistic.check_health()
    assert health['is_healthy'] is True
    assert health['frames_captured'] > 0

    # Stop
    mock_capture_realistic.stop_capture()

    # Verify file
    assert temp_video_file.exists()
    assert temp_video_file.stat().st_size > 0


@pytest.mark.unit_integration
def test_mock_capture_multiple_sessions(mock_capture_fast, temp_recording_dir):
    """Test multiple sequential capture sessions."""
    # Session 1
    file1 = temp_recording_dir / "recording1.mp4"
    mock_capture_fast.start_capture(file1, duration=5)
    mock_capture_fast.stop_capture()

    # Session 2
    file2 = temp_recording_dir / "recording2.mp4"
    mock_capture_fast.start_capture(file2, duration=5)
    mock_capture_fast.stop_capture()

    # Both files should exist
    assert file1.exists()
    assert file2.exists()
