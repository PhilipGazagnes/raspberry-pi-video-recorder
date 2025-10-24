"""
Recording Module Integration Tests

Focused tests following CLAUDE.md: simplicity first, top priorities only.

Tests cover:
1. Mock capture works correctly
2. Camera manager basic operations
3. Recording session lifecycle
4. Factory creates correct implementations
5. Duration tracking and extensions
"""

import tempfile
from pathlib import Path

import pytest

# Import constants
from recording.constants import (
    EXTENSION_DURATION,
    RecordingState,
)

# Import controllers
from recording.controllers.camera_manager import CameraManager
from recording.controllers.recording_session import RecordingSession

# Import factory
from recording.factory import RecordingFactory, create_capture

# Import implementations
from recording.implementations.mock_capture import MockCapture

# Import interfaces
from recording.interfaces.video_capture_interface import (
    CaptureError,
)

# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test recordings"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_capture():
    """Create a mock capture instance with fast timing"""
    capture = MockCapture(simulate_timing=False)
    yield capture
    capture.cleanup()


@pytest.fixture
def camera_manager(mock_capture):
    """Create a camera manager with mock capture"""
    manager = CameraManager(capture=mock_capture)
    yield manager
    manager.cleanup()


# =============================================================================
# MOCK CAPTURE TESTS
# =============================================================================


class TestMockCapture:
    """Test mock capture implementation"""

    def test_mock_capture_initialization(self):
        """MockCapture initializes correctly"""
        capture = MockCapture(simulate_timing=False)

        assert capture.is_capturing() is False
        assert capture.is_available() is True
        assert capture.get_capture_duration() == 0.0

        capture.cleanup()

    def test_start_capture(self, mock_capture, temp_output_dir):
        """MockCapture can start capturing"""
        output_file = temp_output_dir / "test_video.mp4"

        result = mock_capture.start_capture(output_file, duration=10)

        assert result is True
        assert mock_capture.is_capturing() is True
        assert mock_capture.get_output_file() == output_file

    def test_stop_capture(self, mock_capture, temp_output_dir):
        """MockCapture can stop capturing"""
        output_file = temp_output_dir / "test_video.mp4"

        # Start then stop
        mock_capture.start_capture(output_file, duration=10)
        result = mock_capture.stop_capture()

        assert result is True
        assert mock_capture.is_capturing() is False
        assert output_file.exists()

    def test_capture_creates_file(self, mock_capture, temp_output_dir):
        """MockCapture creates video file"""
        output_file = temp_output_dir / "test_video.mp4"

        mock_capture.start_capture(output_file, duration=10)
        mock_capture.stop_capture()

        assert output_file.exists()
        assert output_file.stat().st_size > 0

    def test_get_capture_duration(self, mock_capture, temp_output_dir):
        """MockCapture tracks duration"""
        output_file = temp_output_dir / "test_video.mp4"

        mock_capture.start_capture(output_file, duration=10)

        # Without timing simulation, should return target duration
        duration = mock_capture.get_capture_duration()
        assert duration == 10.0

        mock_capture.stop_capture()

    def test_check_health(self, mock_capture, temp_output_dir):
        """MockCapture health check works"""
        output_file = temp_output_dir / "test_video.mp4"

        # Start capture
        mock_capture.start_capture(output_file, duration=10)

        # Check health
        health = mock_capture.check_health()

        assert "is_healthy" in health
        assert "error_message" in health
        assert "frames_captured" in health
        assert "fps" in health
        assert health["is_healthy"] is True

        mock_capture.stop_capture()

    def test_cannot_start_while_capturing(self, mock_capture, temp_output_dir):
        """MockCapture prevents starting while already capturing"""
        output_file1 = temp_output_dir / "video1.mp4"
        output_file2 = temp_output_dir / "video2.mp4"

        # Start first capture
        mock_capture.start_capture(output_file1, duration=10)

        # Try to start second capture - should fail
        result = mock_capture.start_capture(output_file2, duration=10)

        assert result is False
        assert mock_capture.get_output_file() == output_file1

        mock_capture.stop_capture()

    def test_simulate_start_failure(self, mock_capture, temp_output_dir):
        """MockCapture can simulate start failure"""
        output_file = temp_output_dir / "test_video.mp4"

        # Configure to fail
        mock_capture.simulate_start_failure()

        # Should raise error
        with pytest.raises(CaptureError):
            mock_capture.start_capture(output_file, duration=10)

    def test_reset_test_config(self, mock_capture, temp_output_dir):
        """MockCapture can reset test configuration"""
        output_file = temp_output_dir / "test_video.mp4"

        # Configure to fail
        mock_capture.simulate_start_failure()

        # Reset
        mock_capture.reset_test_config()

        # Should work now
        result = mock_capture.start_capture(output_file, duration=10)
        assert result is True

        mock_capture.stop_capture()


# =============================================================================
# CAMERA MANAGER TESTS
# =============================================================================


class TestCameraManager:
    """Test camera manager"""

    def test_camera_manager_initialization(self, mock_capture):
        """CameraManager initializes correctly"""
        manager = CameraManager(capture=mock_capture)

        assert manager.is_ready() is True
        assert manager.is_recording() is False

        manager.cleanup()

    def test_start_recording(self, camera_manager, temp_output_dir):
        """CameraManager can start recording"""
        output_file = temp_output_dir / "test_video.mp4"

        result = camera_manager.start_recording(output_file, duration=600)

        assert result is True
        assert camera_manager.is_recording() is True

    def test_stop_recording(self, camera_manager, temp_output_dir):
        """CameraManager can stop recording"""
        output_file = temp_output_dir / "test_video.mp4"

        # Start then stop
        camera_manager.start_recording(output_file, duration=600)
        result = camera_manager.stop_recording()

        assert result is True
        assert camera_manager.is_recording() is False

    def test_get_status(self, camera_manager, temp_output_dir):
        """CameraManager provides status"""
        output_file = temp_output_dir / "test_video.mp4"

        camera_manager.start_recording(output_file, duration=600)

        status = camera_manager.get_status()

        assert status is not None
        assert "is_recording" in status
        assert status["is_recording"] is True

    def test_check_health(self, camera_manager, temp_output_dir):
        """CameraManager health check works"""
        output_file = temp_output_dir / "test_video.mp4"

        camera_manager.start_recording(output_file, duration=600)

        health = camera_manager.check_health()

        assert health is not None
        assert "is_healthy" in health


# =============================================================================
# RECORDING SESSION TESTS
# =============================================================================


class TestRecordingSession:
    """Test recording session"""

    def test_recording_session_initialization(self, camera_manager):
        """RecordingSession initializes correctly"""
        session = RecordingSession(camera_manager)

        assert session.state == RecordingState.IDLE
        assert session.get_elapsed_time() == 0.0
        assert session.get_remaining_time() == 0.0

    def test_start_session(self, camera_manager, temp_output_dir):
        """RecordingSession can start"""
        session = RecordingSession(camera_manager)
        output_file = temp_output_dir / "test_video.mp4"

        result = session.start(output_file, duration=600)

        assert result is True
        assert session.state == RecordingState.RECORDING

    def test_stop_session(self, camera_manager, temp_output_dir):
        """RecordingSession can stop"""
        session = RecordingSession(camera_manager)
        output_file = temp_output_dir / "test_video.mp4"

        # Start then stop
        session.start(output_file, duration=600)
        result = session.stop()

        assert result is True
        # Session goes back to IDLE after stopping
        assert session.state == RecordingState.IDLE

    def test_extend_recording(self, camera_manager, temp_output_dir):
        """RecordingSession can extend duration"""
        session = RecordingSession(camera_manager)
        output_file = temp_output_dir / "test_video.mp4"

        # Start recording
        session.start(output_file, duration=600)

        # Extend
        initial_limit = session._current_duration_limit
        result = session.extend()

        assert result is True
        assert session._current_duration_limit == initial_limit + EXTENSION_DURATION
        assert session._extension_count == 1

    def test_callbacks(self, camera_manager, temp_output_dir):
        """RecordingSession callbacks are triggered"""
        session = RecordingSession(camera_manager)
        output_file = temp_output_dir / "test_video.mp4"

        # Track callback invocations
        callbacks_called = {"start": False, "complete": False}

        def on_start():
            callbacks_called["start"] = True

        def on_complete():
            callbacks_called["complete"] = True

        # Register callbacks
        session.on_start = on_start
        session.on_complete = on_complete

        # Start and stop
        session.start(output_file, duration=600)
        session.stop()

        # Callbacks should have been called
        assert callbacks_called["start"] is True
        assert callbacks_called["complete"] is True

    def test_get_status(self, camera_manager, temp_output_dir):
        """RecordingSession provides status information"""
        session = RecordingSession(camera_manager)
        output_file = temp_output_dir / "test_video.mp4"

        session.start(output_file, duration=600)

        status = session.get_status()

        assert status is not None
        assert "state" in status
        assert "elapsed_time" in status
        assert "remaining_time" in status
        assert status["state"] == RecordingState.RECORDING.value


# =============================================================================
# FACTORY TESTS
# =============================================================================


class TestRecordingFactory:
    """Test recording factory"""

    def test_factory_creates_mock(self):
        """Factory creates mock capture"""
        capture = RecordingFactory.create_capture(mode="mock", simulate_timing=False)

        assert isinstance(capture, MockCapture)
        assert capture.is_available() is True

        capture.cleanup()

    def test_factory_convenience_function(self):
        """Convenience create_capture function works"""
        capture = create_capture(force_mock=True, fast_mode=True)

        assert isinstance(capture, MockCapture)
        assert capture.is_available() is True

        capture.cleanup()


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests for recording module"""

    def test_full_recording_workflow(self, temp_output_dir):
        """Full workflow: factory → camera → session → record"""
        # Create capture via factory
        capture = create_capture(force_mock=True, fast_mode=True)

        # Create camera manager
        camera = CameraManager(capture=capture)

        # Create session
        session = RecordingSession(camera)

        # Start recording
        output_file = temp_output_dir / "recording.mp4"
        result = session.start(output_file, duration=600)

        assert result is True
        assert session.state == RecordingState.RECORDING

        # Stop recording
        session.stop()

        assert session.state == RecordingState.IDLE
        assert output_file.exists()

        # Cleanup
        camera.cleanup()
        capture.cleanup()

    def test_recording_with_extension(self, temp_output_dir):
        """Test recording with duration extension"""
        capture = create_capture(force_mock=True, fast_mode=True)
        camera = CameraManager(capture=capture)
        session = RecordingSession(camera)

        output_file = temp_output_dir / "recording.mp4"

        # Start recording
        session.start(output_file, duration=600)

        # Extend once
        session.extend()
        assert session._extension_count == 1

        # Extend again
        session.extend()
        assert session._extension_count == 2

        # Stop
        session.stop()

        assert output_file.exists()

        # Cleanup
        camera.cleanup()
        capture.cleanup()

    def test_session_without_explicit_camera(self, mock_capture, temp_output_dir):
        """Session works with camera manager created from factory"""
        # Create camera manager without explicit capture
        # (would auto-create in real usage, but we inject mock here)
        camera = CameraManager(capture=mock_capture)
        session = RecordingSession(camera)

        output_file = temp_output_dir / "recording.mp4"
        result = session.start(output_file, duration=600)

        assert result is True
        assert session.state == RecordingState.RECORDING

        session.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
