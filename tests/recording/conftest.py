"""
Recording Test Configuration and Fixtures

Shared fixtures for recording module tests.
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from recording.controllers.camera_manager import CameraManager
from recording.controllers.recording_session import RecordingSession
from recording.implementations.mock_capture import MockCapture

# =============================================================================
# CAPTURE FIXTURES
# =============================================================================


@pytest.fixture
def mock_capture_fast():
    """
    Provide MockCapture without timing simulation (fast tests).

    Usage:
        def test_capture(mock_capture_fast):
            mock_capture_fast.start_capture(Path("test.mp4"))
    """
    capture = MockCapture(simulate_timing=False)
    yield capture
    capture.cleanup()


@pytest.fixture
def mock_capture_realistic():
    """
    Provide MockCapture with timing simulation (realistic tests).

    Usage:
        def test_timing(mock_capture_realistic):
            mock_capture_realistic.start_capture(Path("test.mp4"), duration=10)
    """
    capture = MockCapture(simulate_timing=True)
    yield capture
    capture.cleanup()


# =============================================================================
# CAMERA MANAGER FIXTURES
# =============================================================================


@pytest.fixture
def camera_manager(mock_capture_fast):
    """
    Provide CameraManager with fast mock capture.

    Usage:
        def test_camera(camera_manager):
            camera_manager.start_recording(Path("test.mp4"))
    """
    manager = CameraManager(capture=mock_capture_fast)
    yield manager
    manager.cleanup()


@pytest.fixture
def camera_manager_realistic(mock_capture_realistic):
    """
    Provide CameraManager with realistic timing.

    For tests that need realistic duration tracking.
    """
    manager = CameraManager(capture=mock_capture_realistic)
    yield manager
    manager.cleanup()


# =============================================================================
# RECORDING SESSION FIXTURES
# =============================================================================


@pytest.fixture
def recording_session(camera_manager):
    """
    Provide RecordingSession with camera manager.

    Usage:
        def test_session(recording_session):
            recording_session.start(Path("test.mp4"), duration=60)
    """
    session = RecordingSession(camera_manager)
    yield session
    session.cleanup()


# =============================================================================
# TEMPORARY FILE/DIRECTORY FIXTURES
# =============================================================================


@pytest.fixture
def temp_video_file():
    """
    Provide temporary file path for video output.

    File is automatically cleaned up after test.

    Usage:
        def test_recording(temp_video_file):
            # Use temp_video_file as output path
    """
    temp_dir = Path(tempfile.mkdtemp())
    video_file = temp_dir / "test_recording.mp4"

    yield video_file

    # Cleanup
    if video_file.exists():
        video_file.unlink()
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def temp_recording_dir():
    """
    Provide temporary directory for multiple recordings.

    Directory is automatically cleaned up after test.

    Usage:
        def test_multiple(temp_recording_dir):
            file1 = temp_recording_dir / "recording1.mp4"
            file2 = temp_recording_dir / "recording2.mp4"
    """
    temp_dir = Path(tempfile.mkdtemp())

    yield temp_dir

    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


# =============================================================================
# CALLBACK TRACKING FIXTURES
# =============================================================================


@pytest.fixture
def callback_tracker():
    """
    Provide helper for tracking callback calls.

    Usage:
        def test_callback(recording_session, callback_tracker):
            recording_session.on_warning = callback_tracker.track
            # ... trigger warning ...
            assert callback_tracker.was_called()
    """

    class CallbackTracker:
        def __init__(self):
            self.calls = []

        def track(self, *args, **kwargs):
            """Record a callback invocation"""
            self.calls.append({"args": args, "kwargs": kwargs})

        def was_called(self) -> bool:
            """Check if callback was called"""
            return len(self.calls) > 0

        def get_call_count(self) -> int:
            """Get number of times callback was called"""
            return len(self.calls)

        def get_last_call(self):
            """Get arguments from last call"""
            return self.calls[-1] if self.calls else None

        def get_all_calls(self):
            """Get all calls"""
            return self.calls.copy()

        def reset(self):
            """Clear call history"""
            self.calls.clear()

    return CallbackTracker()


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================


def pytest_configure(config):
    """
    Configure pytest with custom markers for recording tests.
    """
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "unit_integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "requires_ffmpeg: Tests requiring FFmpeg")
