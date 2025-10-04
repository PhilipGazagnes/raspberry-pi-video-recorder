"""
Camera Manager Tests

Tests for CameraManager showing:
- Lifecycle management
- Health monitoring
- Error handling
- Status reporting

To run:
    pytest tests/recording/controllers/test_camera_manager.py -v
"""

import time
import pytest
from pathlib import Path

from recording.controllers.camera_manager import CameraManager


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================

@pytest.mark.unit
def test_camera_manager_initialization(mock_capture_fast):
    """Test camera manager initializes correctly."""
    manager = CameraManager(capture=mock_capture_fast)

    assert manager.capture is mock_capture_fast
    assert manager.is_ready() is True

    manager.cleanup()


# =============================================================================
# READINESS TESTS
# =============================================================================

@pytest.mark.unit
def test_camera_manager_is_ready(camera_manager):
    """Test is_ready() check."""
    # Should be ready initially
    assert camera_manager.is_ready() is True


@pytest.mark.unit
def test_camera_manager_not_ready_when_recording(camera_manager, temp_video_file):
    """Test not ready when already recording."""
    camera_manager.start_recording(temp_video_file)

    # Should not be ready now
    assert camera_manager.is_ready() is False

    camera_manager.stop_recording()


# =============================================================================
# RECORDING TESTS
# =============================================================================

@pytest.mark.unit
def test_camera_manager_start_recording(camera_manager, temp_video_file):
    """Test starting recording."""
    success = camera_manager.start_recording(temp_video_file, duration=60)

    assert success is True
    assert camera_manager.is_recording() is True
    assert camera_manager.get_output_file() == temp_video_file

    camera_manager.stop_recording()


@pytest.mark.unit
def test_camera_manager_stop_recording(camera_manager, temp_video_file):
    """Test stopping recording."""
    camera_manager.start_recording(temp_video_file)

    success = camera_manager.stop_recording()

    assert success is True
    assert camera_manager.is_recording() is False


@pytest.mark.unit
def test_camera_manager_cannot_start_twice(camera_manager, temp_video_file):
    """Test cannot start recording twice."""
    camera_manager.start_recording(temp_video_file)

    # Try to start again
    temp_file2 = temp_video_file.parent / "test2.mp4"
    success = camera_manager.start_recording(temp_file2)

    assert success is False


@pytest.mark.unit
def test_camera_manager_stop_when_not_recording(camera_manager):
    """Test stop when not recording."""
    success = camera_manager.stop_recording()

    assert success is False


# =============================================================================
# DURATION TRACKING TESTS
# =============================================================================

@pytest.mark.unit
def test_camera_manager_get_recording_duration(camera_manager_realistic, temp_video_file):
    """Test getting recording duration."""
    camera_manager_realistic.start_recording(temp_video_file)

    time.sleep(0.3)

    duration = camera_manager_realistic.get_recording_duration()

    # Should be around 0.3 seconds
    assert 0.2 < duration < 0.4

    camera_manager_realistic.stop_recording()


@pytest.mark.unit
def test_camera_manager_duration_zero_when_not_recording(camera_manager):
    """Test duration is zero when not recording."""
    duration = camera_manager.get_recording_duration()

    assert duration == 0.0


# =============================================================================
# HEALTH MONITORING TESTS
# =============================================================================

@pytest.mark.unit
def test_camera_manager_check_health_not_recording(camera_manager):
    """Test health check when not recording."""
    health = camera_manager.check_health()

    assert health['is_healthy'] is False
    assert "not running" in health['error_message'].lower()


@pytest.mark.unit
def test_camera_manager_check_health_recording(camera_manager, temp_video_file):
    """Test health check during recording."""
    camera_manager.start_recording(temp_video_file)

    health = camera_manager.check_health()

    assert health['is_healthy'] is True
    assert health['error_message'] is None

    camera_manager.stop_recording()


@pytest.mark.unit
def test_camera_manager_health_consecutive_failures(mock_capture_realistic):
    """Test tracking consecutive health check failures."""
    manager = CameraManager(capture=mock_capture_realistic)

    # Start recording
    temp_file = Path("/tmp/test.mp4")
    manager.start_recording(temp_file, duration=10)

    # Simulate crash
    mock_capture_realistic.simulate_crash_during_capture(after_seconds=0.1)
    time.sleep(0.2)

    # Multiple health checks should track failures
    health1 = manager.check_health(force=True)
    assert health1['consecutive_failures'] == 1

    health2 = manager.check_health(force=True)
    assert health2['consecutive_failures'] == 2

    health3 = manager.check_health(force=True)
    assert health3['consecutive_failures'] == 3
    assert health3['critical'] is True

    manager.cleanup()


# =============================================================================
# STATUS TESTS
# =============================================================================

@pytest.mark.unit
def test_camera_manager_get_status(camera_manager, temp_video_file):
    """Test get_status() returns complete information."""
    camera_manager.start_recording(temp_video_file, duration=60)

    status = camera_manager.get_status()

    assert 'is_available' in status
    assert 'is_ready' in status
    assert 'is_recording' in status
    assert 'recording_duration' in status
    assert 'output_file' in status
    assert 'health' in status

    assert status['is_recording'] is True
    assert status['output_file'] == str(temp_video_file)

    camera_manager.stop_recording()


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

@pytest.mark.unit
def test_camera_manager_handles_capture_error(temp_video_file):
    """Test manager handles capture start errors gracefully."""
    from recording.implementations.mock_capture import MockCapture

    mock = MockCapture(simulate_timing=False)
    mock.simulate_start_failure()

    manager = CameraManager(capture=mock)

    # Should handle error gracefully
    with pytest.raises(Exception):  # CaptureError propagates
        manager.start_recording(temp_video_file)

    manager.cleanup()


# =============================================================================
# CLEANUP TESTS
# =============================================================================

@pytest.mark.unit
def test_camera_manager_cleanup_stops_recording(camera_manager, temp_video_file):
    """Test cleanup stops active recording."""
    camera_manager.start_recording(temp_video_file)

    assert camera_manager.is_recording() is True

    camera_manager.cleanup()

    assert camera_manager.is_recording() is False


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

@pytest.mark.unit_integration
def test_camera_manager_complete_workflow(camera_manager_realistic, temp_video_file):
    """Integration test: Complete recording workflow."""
    # Check ready
    assert camera_manager_realistic.is_ready() is True

    # Start recording
    success = camera_manager_realistic.start_recording(temp_video_file, duration=1.0)
    assert success is True

    # Check health during recording
    time.sleep(0.3)
    health = camera_manager_realistic.check_health()
    assert health['is_healthy'] is True

    # Get status
    status = camera_manager_realistic.get_status()
    assert status['is_recording'] is True
    assert status['recording_duration'] > 0

    # Stop
    success = camera_manager_realistic.stop_recording()
    assert success is True

    # Should be ready again
    assert camera_manager_realistic.is_ready() is True


@pytest.mark.unit_integration
def test_camera_manager_multiple_recordings(camera_manager, temp_recording_dir):
    """Test multiple sequential recordings."""
    # Recording 1
    file1 = temp_recording_dir / "rec1.mp4"
    camera_manager.start_recording(file1, duration=10)
    camera_manager.stop_recording()

    # Recording 2
    file2 = temp_recording_dir / "rec2.mp4"
    camera_manager.start_recording(file2, duration=10)
    camera_manager.stop_recording()

    # Recording 3
    file3 = temp_recording_dir / "rec3.mp4"
    camera_manager.start_recording(file3, duration=10)
    camera_manager.stop_recording()

    # All should exist
    assert file1.exists()
    assert file2.exists()
    assert file3.exists()
