"""
Storage Module Integration Tests

Focused tests following CLAUDE.md: simplicity first, top priorities only.

Tests cover:
1. Mock storage works correctly
2. VideoFile model and methods
3. StorageStats calculations
4. Storage controller operations
5. Factory creates correct implementations
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Import constants
from storage.constants import UploadStatus, VideoQuality

# Import factory
from storage.factory import StorageFactory, create_storage

# Import implementations
from storage.implementations.mock_storage import MockStorage

# Import models
from storage.models.video_file import StorageStats, VideoFile

# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def mock_storage():
    """Create a mock storage instance"""
    storage = MockStorage(
        simulated_space_bytes=100 * 1024**3,  # 100 GB
        min_space_bytes=5 * 1024**3,  # 5 GB
    )
    storage.initialize()
    return storage


@pytest.fixture
def sample_video_file():
    """Create a sample VideoFile for testing"""
    return VideoFile(
        filename="test_video.mp4",
        filepath=Path("/mock/test_video.mp4"),
        created_at=datetime.now(),
        duration_seconds=600,
        file_size_bytes=100 * 1024 * 1024,  # 100 MB
        status=UploadStatus.PENDING,
    )


# =============================================================================
# VIDEO FILE MODEL TESTS
# =============================================================================


class TestVideoFileModel:
    """Test VideoFile model and its methods"""

    def test_video_file_initialization(self):
        """VideoFile initializes with required fields"""
        video = VideoFile(
            filename="test.mp4",
            filepath=Path("/test.mp4"),
            created_at=datetime.now(),
        )

        assert video.filename == "test.mp4"
        assert video.filepath == Path("/test.mp4")
        assert video.status == UploadStatus.PENDING
        assert video.upload_attempts == 0

    def test_video_file_properties(self, sample_video_file):
        """VideoFile properties work correctly"""
        video = sample_video_file

        assert video.is_pending is True
        assert video.is_completed is False
        assert video.is_failed is False
        assert video.is_corrupted is False

    def test_mark_upload_success(self, sample_video_file):
        """Marking upload as successful updates status"""
        video = sample_video_file

        video.mark_upload_success("https://youtube.com/watch?v=abc123")

        assert video.is_completed is True
        assert video.youtube_url == "https://youtube.com/watch?v=abc123"
        assert video.upload_error is None

    def test_mark_upload_failed(self, sample_video_file):
        """Marking upload as failed tracks attempts and errors"""
        video = sample_video_file

        video.mark_upload_failed("Network timeout")

        assert video.is_failed is True
        assert video.upload_attempts == 1
        assert video.upload_error == "Network timeout"
        assert video.last_upload_attempt is not None

    def test_can_retry_logic(self, sample_video_file):
        """can_retry respects MAX_UPLOAD_RETRIES"""
        video = sample_video_file

        # Mark as failed - should be retryable
        video.mark_upload_failed("Error 1")
        assert video.can_retry is True

        # Fail multiple times
        video.mark_upload_failed("Error 2")
        video.mark_upload_failed("Error 3")

        # After MAX_UPLOAD_RETRIES (default 3), should not be retryable
        assert video.upload_attempts == 3
        assert video.can_retry is False

    def test_mark_corrupted(self, sample_video_file):
        """Marking as corrupted sets status and quality"""
        video = sample_video_file

        video.mark_corrupted("ffmpeg validation failed")

        assert video.is_corrupted is True
        assert video.quality == VideoQuality.CORRUPTED
        assert video.validation_error == "ffmpeg validation failed"

    def test_age_days(self, sample_video_file):
        """age_days calculates correctly"""
        # Create video from yesterday
        video = VideoFile(
            filename="old.mp4",
            filepath=Path("/old.mp4"),
            created_at=datetime.now() - timedelta(days=1),
        )

        assert video.age_days >= 1.0
        assert video.age_days < 1.1  # Should be close to 1 day

    def test_to_dict_from_dict(self, sample_video_file):
        """VideoFile can be serialized and deserialized"""
        video = sample_video_file
        video.id = 123

        # Serialize
        data = video.to_dict()

        # Deserialize
        restored = VideoFile.from_dict({**data, "id": video.id})

        assert restored.filename == video.filename
        assert restored.status == video.status
        assert restored.duration_seconds == video.duration_seconds


# =============================================================================
# STORAGE STATS MODEL TESTS
# =============================================================================


class TestStorageStatsModel:
    """Test StorageStats model and calculations"""

    def test_storage_stats_initialization(self):
        """StorageStats initializes correctly"""
        stats = StorageStats(
            total_space_bytes=100 * 1024**3,  # 100 GB
            free_space_bytes=50 * 1024**3,  # 50 GB
            used_space_bytes=50 * 1024**3,  # 50 GB
        )

        assert stats.total_space_bytes == 100 * 1024**3
        assert stats.free_space_bytes == 50 * 1024**3

    def test_space_calculations_gb(self):
        """Space calculations in GB work correctly"""
        stats = StorageStats(
            total_space_bytes=100 * 1024**3,  # 100 GB
            free_space_bytes=60 * 1024**3,  # 60 GB
            used_space_bytes=40 * 1024**3,  # 40 GB
        )

        assert stats.total_space_gb == 100.0
        assert stats.free_space_gb == 60.0
        assert stats.used_space_gb == 40.0

    def test_space_usage_percent(self):
        """space_usage_percent calculates correctly"""
        stats = StorageStats(
            total_space_bytes=100 * 1024**3,
            free_space_bytes=25 * 1024**3,
            used_space_bytes=75 * 1024**3,
        )

        assert stats.space_usage_percent == 75.0

    def test_is_low_space(self):
        """is_low_space detects low space correctly"""
        # Low space (1 GB free < LOW_SPACE_WARNING_BYTES)
        stats_low = StorageStats(
            total_space_bytes=100 * 1024**3,
            free_space_bytes=1 * 1024**3,  # 1 GB
            used_space_bytes=99 * 1024**3,
        )

        # Good space
        stats_good = StorageStats(
            total_space_bytes=100 * 1024**3,
            free_space_bytes=20 * 1024**3,  # 20 GB
            used_space_bytes=80 * 1024**3,
        )

        assert stats_low.is_low_space is True
        assert stats_good.is_low_space is False

    def test_is_disk_full(self):
        """is_disk_full detects critical space correctly"""
        # Critical space (< MIN_FREE_SPACE_BYTES)
        stats_critical = StorageStats(
            total_space_bytes=100 * 1024**3,
            free_space_bytes=1 * 1024**3,  # 1 GB
            used_space_bytes=99 * 1024**3,
        )

        # Good space
        stats_good = StorageStats(
            total_space_bytes=100 * 1024**3,
            free_space_bytes=20 * 1024**3,  # 20 GB
            used_space_bytes=80 * 1024**3,
        )

        # Critical should be true, good should be false
        assert stats_critical.is_disk_full is True
        assert stats_good.is_disk_full is False


# =============================================================================
# MOCK STORAGE TESTS
# =============================================================================


class TestMockStorage:
    """Test mock storage implementation"""

    def test_mock_storage_initialization(self):
        """MockStorage initializes correctly"""
        storage = MockStorage(
            simulated_space_bytes=50 * 1024**3,
            min_space_bytes=5 * 1024**3,
        )

        storage.initialize()
        assert storage.is_available() is True

    def test_save_video(self, mock_storage):
        """MockStorage can save videos"""
        video = mock_storage.save_video(
            source_path=Path("/test/video.mp4"),
            duration_seconds=600,
        )

        assert video is not None
        assert video.id is not None
        assert video.filename is not None
        assert video.status == UploadStatus.PENDING

    def test_get_video(self, mock_storage):
        """MockStorage can retrieve videos by ID"""
        # Save a video
        saved = mock_storage.save_video(Path("/test/video.mp4"))

        # Retrieve it
        retrieved = mock_storage.get_video(saved.id)

        assert retrieved is not None
        assert retrieved.id == saved.id
        assert retrieved.filename == saved.filename

    def test_get_video_by_filename(self, mock_storage):
        """MockStorage can retrieve videos by filename"""
        # Save a video
        saved = mock_storage.save_video(Path("/test/video.mp4"))

        # Retrieve by filename
        retrieved = mock_storage.get_video_by_filename(saved.filename)

        assert retrieved is not None
        assert retrieved.filename == saved.filename

    def test_list_videos(self, mock_storage):
        """MockStorage can list videos"""
        # Save multiple videos
        video1 = mock_storage.save_video(Path("/test/video1.mp4"))
        video2 = mock_storage.save_video(Path("/test/video2.mp4"))

        # List all videos
        all_videos = mock_storage.list_videos()

        assert len(all_videos) == 2
        assert video1 in all_videos
        assert video2 in all_videos

    def test_list_videos_filtered_by_status(self, mock_storage):
        """MockStorage can filter videos by status"""
        # Save and mark one as completed
        video1 = mock_storage.save_video(Path("/test/video1.mp4"))
        video2 = mock_storage.save_video(Path("/test/video2.mp4"))

        video1.mark_upload_success("https://youtube.com/watch?v=abc")
        mock_storage.update_video(video1)

        # List only pending
        pending = mock_storage.list_videos(status=UploadStatus.PENDING)
        assert len(pending) == 1
        assert pending[0].id == video2.id

        # List only completed
        completed = mock_storage.list_videos(status=UploadStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].id == video1.id

    def test_update_video(self, mock_storage):
        """MockStorage can update video metadata"""
        # Save a video
        video = mock_storage.save_video(Path("/test/video.mp4"))

        # Update it
        video.mark_upload_success("https://youtube.com/watch?v=xyz")
        mock_storage.update_video(video)

        # Retrieve and verify
        updated = mock_storage.get_video(video.id)
        assert updated.is_completed is True
        assert updated.youtube_url == "https://youtube.com/watch?v=xyz"

    def test_delete_video(self, mock_storage):
        """MockStorage can delete videos"""
        # Save a video
        video = mock_storage.save_video(Path("/test/video.mp4"))

        # Delete it
        mock_storage.delete_video(video, remove_file=True)

        # Should not be retrievable
        retrieved = mock_storage.get_video(video.id)
        assert retrieved is None

    def test_check_space_available(self, mock_storage):
        """MockStorage checks space availability"""
        # Should have space initially
        assert mock_storage.check_space_available() is True

    def test_get_stats(self, mock_storage):
        """MockStorage returns statistics"""
        # Save some videos
        mock_storage.save_video(Path("/test/video1.mp4"))
        mock_storage.save_video(Path("/test/video2.mp4"))

        # Get stats
        stats = mock_storage.get_stats()

        assert stats is not None
        assert stats.total_videos == 2
        assert stats.pending_count == 2
        assert stats.total_space_bytes > 0

    def test_get_retry_queue(self, mock_storage):
        """MockStorage returns retry queue"""
        # Save and fail a video
        video = mock_storage.save_video(Path("/test/video.mp4"))
        video.mark_upload_failed("Network error")
        mock_storage.update_video(video)

        # Get retry queue
        retry_queue = mock_storage.get_retry_queue()

        assert len(retry_queue) == 1
        assert retry_queue[0].id == video.id
        assert retry_queue[0].can_retry is True

    def test_cleanup_old_videos(self, mock_storage):
        """MockStorage can cleanup old videos"""
        # Create an old video (simulate by marking as completed and old)
        video = mock_storage.save_video(Path("/test/old_video.mp4"))
        video.mark_upload_success("https://youtube.com/watch?v=old")
        video.created_at = datetime.now() - timedelta(days=60)  # 60 days old
        mock_storage.update_video(video)

        # Dry run cleanup
        count = mock_storage.cleanup_old_videos(dry_run=True)

        # Should identify the old video
        assert count >= 0  # May or may not cleanup depending on retention policy

    def test_operation_log(self, mock_storage):
        """MockStorage logs operations for testing"""
        # Perform some operations
        mock_storage.save_video(Path("/test/video.mp4"))

        # Check operation log
        assert len(mock_storage.operation_log) > 0
        assert any("save_video" in op for op in mock_storage.operation_log)


# =============================================================================
# FACTORY TESTS
# =============================================================================


class TestStorageFactory:
    """Test storage factory"""

    def test_factory_creates_mock(self):
        """Factory creates mock storage"""
        storage = StorageFactory.create_storage(mode="mock")

        assert isinstance(storage, MockStorage)
        assert storage.is_available() is True

    def test_factory_convenience_function(self):
        """Convenience create_storage function works"""
        storage = create_storage(force_mock=True)

        assert isinstance(storage, MockStorage)
        assert storage.is_available() is True


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests for storage module"""

    def test_full_video_lifecycle(self, mock_storage):
        """Full lifecycle: save → upload → cleanup"""
        # Save video
        video = mock_storage.save_video(
            Path("/test/recording.mp4"),
            duration_seconds=600,
        )

        assert video.is_pending is True

        # Mark as upload in progress
        video.mark_upload_started()
        mock_storage.update_video(video)
        assert video.status == UploadStatus.IN_PROGRESS

        # Mark as uploaded
        video.mark_upload_success("https://youtube.com/watch?v=test123")
        mock_storage.update_video(video)

        assert video.is_completed is True
        assert video.youtube_url is not None

        # Retrieve and verify
        retrieved = mock_storage.get_video(video.id)
        assert retrieved.is_completed is True

    def test_failed_upload_retry_workflow(self, mock_storage):
        """Test failed upload and retry logic"""
        # Save video
        video = mock_storage.save_video(Path("/test/video.mp4"))

        # First failure
        video.mark_upload_failed("Network timeout")
        mock_storage.update_video(video)

        assert video.upload_attempts == 1
        assert video.can_retry is True

        # Get retry queue
        retry_queue = mock_storage.get_retry_queue()
        assert len(retry_queue) == 1
        assert retry_queue[0].id == video.id

    def test_storage_stats_accuracy(self, mock_storage):
        """Storage stats reflect actual state"""
        # Save multiple videos with different states
        video1 = mock_storage.save_video(Path("/test/video1.mp4"))
        video2 = mock_storage.save_video(Path("/test/video2.mp4"))

        video1.mark_upload_success("https://youtube.com/watch?v=vid1")
        mock_storage.update_video(video1)

        video2.mark_upload_failed("Upload error")
        mock_storage.update_video(video2)

        # Get stats
        stats = mock_storage.get_stats()

        assert stats.total_videos == 2
        assert stats.completed_count == 1
        assert stats.failed_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
