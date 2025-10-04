"""
Storage Test Configuration and Fixtures

This file contains pytest fixtures shared across storage tests.
Mirrors the pattern from hardware/conftest.py.

To use pytest:
    pip install pytest
    pytest tests/storage/
"""

import tempfile
from pathlib import Path

import pytest

from storage import StorageController, StorageConfig, UploadStatus
from storage.implementations.local_storage import LocalStorage
from storage.implementations.mock_storage import MockStorage


# =============================================================================
# STORAGE FIXTURES
# =============================================================================

@pytest.fixture
def mock_storage():
    """
    Provide a fresh MockStorage instance for each test.

    Usage:
        def test_something(mock_storage):
            mock_storage.save_video(Path("/fake/video.mp4"))
    """
    storage = MockStorage()
    yield storage
    storage.cleanup()


@pytest.fixture
def mock_storage_with_videos(mock_storage):
    """
    Provide MockStorage with some pre-loaded test videos.

    Useful when tests need existing videos to work with.

    Usage:
        def test_cleanup(mock_storage_with_videos):
            # Already has pending and completed videos
    """
    # Add some pending videos
    mock_storage.add_fake_video("recording_001.mp4", UploadStatus.PENDING)
    mock_storage.add_fake_video("recording_002.mp4", UploadStatus.PENDING)

    # Add some completed videos
    mock_storage.add_fake_video("recording_003.mp4", UploadStatus.COMPLETED)
    mock_storage.add_fake_video("recording_004.mp4", UploadStatus.COMPLETED)

    # Add a failed video
    mock_storage.add_fake_video("recording_005.mp4", UploadStatus.FAILED)

    return mock_storage


@pytest.fixture
def temp_storage_dir():
    """
    Provide a temporary directory for storage tests.

    Automatically cleaned up after test.

    Usage:
        def test_local_storage(temp_storage_dir):
            config = StorageConfig()
            config.set('storage_base_path', str(temp_storage_dir))
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def local_storage_config(temp_storage_dir):
    """
    Provide a StorageConfig configured with temp directory.

    Usage:
        def test_with_config(local_storage_config):
            storage = LocalStorage(local_storage_config)
    """
    config = StorageConfig()
    config.set('storage_base_path', str(temp_storage_dir), save=False)
    config.set('min_free_space_bytes', 1024 * 1024, save=False)  # 1 MB for testing
    config.set('uploaded_retention_days', 1, save=False)  # Short retention for tests
    return config


@pytest.fixture
def local_storage(local_storage_config):
    """
    Provide LocalStorage with temp directory.

    Usage:
        def test_real_storage(local_storage):
            video = local_storage.save_video(Path("/path/to/video.mp4"))
    """
    storage = LocalStorage(local_storage_config)
    storage.initialize()
    yield storage
    storage.cleanup()


# =============================================================================
# CONTROLLER FIXTURES
# =============================================================================

@pytest.fixture
def storage_controller(mock_storage):
    """
    Provide StorageController with mock storage.

    Usage:
        def test_controller(storage_controller):
            stats = storage_controller.get_stats()
    """
    controller = StorageController(storage_impl=mock_storage)
    yield controller
    controller.cleanup()


@pytest.fixture
def storage_controller_with_videos(mock_storage_with_videos):
    """
    Provide StorageController with pre-loaded videos.

    Usage:
        def test_pending_uploads(storage_controller_with_videos):
            pending = storage_controller_with_videos.get_pending_uploads()
            assert len(pending) > 0
    """
    controller = StorageController(storage_impl=mock_storage_with_videos)
    yield controller
    controller.cleanup()


# =============================================================================
# HELPER FIXTURES
# =============================================================================

@pytest.fixture
def event_tracker():
    """
    Provide a helper for tracking event callbacks.

    Similar to callback_tracker from hardware tests.

    Usage:
        def test_events(storage_controller, event_tracker):
            storage_controller.on_disk_full = event_tracker.track
            # ... trigger event ...
            assert event_tracker.was_called()
    """
    class EventTracker:
        def __init__(self):
            self.calls = []
            self.call_args = []

        def track(self, *args, **kwargs):
            """Record an event invocation"""
            self.calls.append({'args': args, 'kwargs': kwargs})
            if args:
                self.call_args.append(args[0])

        def was_called(self) -> bool:
            """Check if event was triggered"""
            return len(self.calls) > 0

        def get_call_count(self) -> int:
            """Get number of times event was triggered"""
            return len(self.calls)

        def get_last_call(self):
            """Get arguments from last call"""
            return self.calls[-1] if self.calls else None

        def get_all_call_args(self):
            """Get all call arguments"""
            return self.call_args

        def reset(self):
            """Clear call history"""
            self.calls.clear()
            self.call_args.clear()

    return EventTracker()


@pytest.fixture
def sample_video_file(temp_storage_dir):
    """
    Create a sample video file for testing.

    Returns path to a small test file.

    Usage:
        def test_save_video(storage_controller, sample_video_file):
            video = storage_controller.save_recording(sample_video_file)
    """
    # Create a small fake video file
    video_path = temp_storage_dir / "test_video.mp4"

    # Write some dummy data (1 MB)
    video_path.write_bytes(b"fake video data" * 70000)

    return video_path


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """
    Configure pytest with custom markers.

    Same markers as hardware tests for consistency.
    """
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "unit_integration: Unit integration tests")
    config.addinivalue_line("markers", "integration: Full integration tests")
    config.addinivalue_line("markers", "slow: Slow tests (use sparingly)")
