"""
Metadata Manager Tests

Tests for SQLite metadata management showing:
- Database CRUD operations
- Video querying
- Status tracking
- Retry queue management

To run these tests:
    pytest tests/storage/managers/test_metadata_manager.py -v
"""

from datetime import datetime
from pathlib import Path

import pytest

from storage.constants import UploadStatus
from storage.managers.metadata_manager import MetadataManager
from storage.models.video_file import VideoFile

# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


@pytest.mark.unit
def test_metadata_manager_initialization(temp_storage_dir):
    """
    Test metadata manager initializes correctly.

    Should:
    - Create database file
    - Initialize schema
    - Be ready for operations
    """
    manager = MetadataManager(temp_storage_dir)

    # Database should exist
    db_path = temp_storage_dir / "video_metadata.db"
    assert db_path.exists()

    manager.cleanup()


# =============================================================================
# INSERT TESTS
# =============================================================================


@pytest.mark.unit
def test_insert_video(temp_storage_dir):
    """
    Test inserting a new video record.

    Should:
    - Insert video into database
    - Assign ID
    - Return video with ID set
    """
    manager = MetadataManager(temp_storage_dir)

    # Create video
    video = VideoFile(
        filename="test_video.mp4",
        filepath=Path("/fake/test_video.mp4"),
        created_at=datetime.now(),
        duration_seconds=600,
        file_size_bytes=100_000_000,
        status=UploadStatus.PENDING,
    )

    # Insert
    result = manager.insert_video(video)

    # Should have ID
    assert result.id is not None
    assert result.id > 0

    manager.cleanup()


@pytest.mark.unit
def test_insert_video_duplicate_filename(temp_storage_dir):
    """
    Test inserting video with duplicate filename fails.

    Should raise StorageError.
    """
    from storage.interfaces.storage_interface import StorageError

    manager = MetadataManager(temp_storage_dir)

    # Create video
    video = VideoFile(
        filename="duplicate.mp4",
        filepath=Path("/fake/duplicate.mp4"),
        created_at=datetime.now(),
        status=UploadStatus.PENDING,
    )

    # Insert first time
    manager.insert_video(video)

    # Try to insert again with same filename
    video2 = VideoFile(
        filename="duplicate.mp4",  # Same filename
        filepath=Path("/fake/duplicate.mp4"),
        created_at=datetime.now(),
        status=UploadStatus.PENDING,
    )

    with pytest.raises(StorageError):
        manager.insert_video(video2)

    manager.cleanup()


# =============================================================================
# UPDATE TESTS
# =============================================================================


@pytest.mark.unit
def test_update_video(temp_storage_dir):
    """
    Test updating a video record.

    Should update all fields in database.
    """
    manager = MetadataManager(temp_storage_dir)

    # Insert video
    video = VideoFile(
        filename="test_video.mp4",
        filepath=Path("/fake/test_video.mp4"),
        created_at=datetime.now(),
        status=UploadStatus.PENDING,
    )
    video = manager.insert_video(video)

    # Update fields
    video.status = UploadStatus.COMPLETED
    video.youtube_url = "https://youtube.com/..."
    video.upload_attempts = 1

    # Update
    manager.update_video(video)

    # Retrieve and verify
    retrieved = manager.get_video(video.id)
    assert retrieved.status == UploadStatus.COMPLETED
    assert retrieved.youtube_url == "https://youtube.com/..."

    manager.cleanup()


# =============================================================================
# RETRIEVAL TESTS
# =============================================================================


@pytest.mark.unit
def test_get_video_by_id(temp_storage_dir):
    """
    Test retrieving video by ID.
    """
    manager = MetadataManager(temp_storage_dir)

    # Insert video
    video = VideoFile(
        filename="test_video.mp4",
        filepath=Path("/fake/test_video.mp4"),
        created_at=datetime.now(),
        status=UploadStatus.PENDING,
    )
    video = manager.insert_video(video)

    # Retrieve
    retrieved = manager.get_video(video.id)

    assert retrieved is not None
    assert retrieved.id == video.id
    assert retrieved.filename == video.filename

    manager.cleanup()


@pytest.mark.unit
def test_get_video_by_id_not_found(temp_storage_dir):
    """
    Test retrieving nonexistent video returns None.
    """
    manager = MetadataManager(temp_storage_dir)

    # Try to get nonexistent video
    video = manager.get_video(99999)

    assert video is None

    manager.cleanup()


@pytest.mark.unit
def test_get_video_by_filename(temp_storage_dir):
    """
    Test retrieving video by filename.
    """
    manager = MetadataManager(temp_storage_dir)

    # Insert video
    video = VideoFile(
        filename="unique_video.mp4",
        filepath=Path("/fake/unique_video.mp4"),
        created_at=datetime.now(),
        status=UploadStatus.PENDING,
    )
    manager.insert_video(video)

    # Retrieve by filename
    retrieved = manager.get_video_by_filename("unique_video.mp4")

    assert retrieved is not None
    assert retrieved.filename == "unique_video.mp4"

    manager.cleanup()


# =============================================================================
# LIST/QUERY TESTS
# =============================================================================


@pytest.mark.unit
def test_list_all_videos(temp_storage_dir):
    """
    Test listing all videos.
    """
    manager = MetadataManager(temp_storage_dir)

    # Insert multiple videos
    for i in range(3):
        video = VideoFile(
            filename=f"video_{i}.mp4",
            filepath=Path(f"/fake/video_{i}.mp4"),
            created_at=datetime.now(),
            status=UploadStatus.PENDING,
        )
        manager.insert_video(video)

    # List all
    videos = manager.list_videos()

    assert len(videos) == 3

    manager.cleanup()


@pytest.mark.unit
def test_list_videos_by_status(temp_storage_dir):
    """
    Test listing videos filtered by status.
    """
    manager = MetadataManager(temp_storage_dir)

    # Insert videos with different statuses
    for i in range(2):
        video = VideoFile(
            filename=f"pending_{i}.mp4",
            filepath=Path(f"/fake/pending_{i}.mp4"),
            created_at=datetime.now(),
            status=UploadStatus.PENDING,
        )
        manager.insert_video(video)

    for i in range(3):
        video = VideoFile(
            filename=f"completed_{i}.mp4",
            filepath=Path(f"/fake/completed_{i}.mp4"),
            created_at=datetime.now(),
            status=UploadStatus.COMPLETED,
        )
        manager.insert_video(video)

    # List pending only
    pending = manager.list_videos(status=UploadStatus.PENDING)
    assert len(pending) == 2

    # List completed only
    completed = manager.list_videos(status=UploadStatus.COMPLETED)
    assert len(completed) == 3

    manager.cleanup()


@pytest.mark.unit
def test_list_videos_with_limit(temp_storage_dir):
    """
    Test listing videos with limit.
    """
    manager = MetadataManager(temp_storage_dir)

    # Insert 10 videos
    for i in range(10):
        video = VideoFile(
            filename=f"video_{i}.mp4",
            filepath=Path(f"/fake/video_{i}.mp4"),
            created_at=datetime.now(),
            status=UploadStatus.PENDING,
        )
        manager.insert_video(video)

    # List with limit
    videos = manager.list_videos(limit=5)

    assert len(videos) == 5

    manager.cleanup()


# =============================================================================
# DELETE TESTS
# =============================================================================


@pytest.mark.unit
def test_delete_video(temp_storage_dir):
    """
    Test deleting a video record.
    """
    manager = MetadataManager(temp_storage_dir)

    # Insert video
    video = VideoFile(
        filename="to_delete.mp4",
        filepath=Path("/fake/to_delete.mp4"),
        created_at=datetime.now(),
        status=UploadStatus.PENDING,
    )
    video = manager.insert_video(video)

    # Delete
    manager.delete_video(video.id)

    # Should not exist
    retrieved = manager.get_video(video.id)
    assert retrieved is None

    manager.cleanup()


# =============================================================================
# RETRY QUEUE TESTS
# =============================================================================


@pytest.mark.unit
def test_get_retry_queue(temp_storage_dir):
    """
    Test getting retry queue.

    Should return failed videos under retry limit.
    """
    from storage.constants import MAX_UPLOAD_RETRIES

    manager = MetadataManager(temp_storage_dir)

    # Insert failed video (eligible for retry)
    video1 = VideoFile(
        filename="retry_eligible.mp4",
        filepath=Path("/fake/retry_eligible.mp4"),
        created_at=datetime.now(),
        status=UploadStatus.FAILED,
        upload_attempts=1,
    )
    manager.insert_video(video1)

    # Insert failed video (exceeded retries)
    video2 = VideoFile(
        filename="retry_exceeded.mp4",
        filepath=Path("/fake/retry_exceeded.mp4"),
        created_at=datetime.now(),
        status=UploadStatus.FAILED,
        upload_attempts=MAX_UPLOAD_RETRIES + 1,
    )
    manager.insert_video(video2)

    # Get retry queue
    retry_queue = manager.get_retry_queue()

    # Should only have eligible video
    assert len(retry_queue) == 1
    assert retry_queue[0].filename == "retry_eligible.mp4"

    manager.cleanup()


# =============================================================================
# STATUS COUNT TESTS
# =============================================================================


@pytest.mark.unit
def test_get_count_by_status(temp_storage_dir):
    """
    Test getting video count by status.
    """
    manager = MetadataManager(temp_storage_dir)

    # Insert videos with different statuses
    for i in range(2):
        video = VideoFile(
            filename=f"pending_{i}.mp4",
            filepath=Path(f"/fake/pending_{i}.mp4"),
            created_at=datetime.now(),
            status=UploadStatus.PENDING,
        )
        manager.insert_video(video)

    for i in range(3):
        video = VideoFile(
            filename=f"completed_{i}.mp4",
            filepath=Path(f"/fake/completed_{i}.mp4"),
            created_at=datetime.now(),
            status=UploadStatus.COMPLETED,
        )
        manager.insert_video(video)

    # Get counts
    counts = manager.get_count_by_status()

    assert counts[UploadStatus.PENDING.value] == 2
    assert counts[UploadStatus.COMPLETED.value] == 3

    manager.cleanup()


@pytest.mark.unit
def test_get_total_count(temp_storage_dir):
    """
    Test getting total video count.
    """
    manager = MetadataManager(temp_storage_dir)

    # Insert videos
    for i in range(5):
        video = VideoFile(
            filename=f"video_{i}.mp4",
            filepath=Path(f"/fake/video_{i}.mp4"),
            created_at=datetime.now(),
            status=UploadStatus.PENDING,
        )
        manager.insert_video(video)

    # Get total
    total = manager.get_total_count()

    assert total == 5

    manager.cleanup()


# =============================================================================
# CLEANUP TESTS
# =============================================================================


@pytest.mark.unit
def test_cleanup(temp_storage_dir):
    """
    Test cleanup closes database properly.
    """
    manager = MetadataManager(temp_storage_dir)

    # Insert video
    video = VideoFile(
        filename="test.mp4",
        filepath=Path("/fake/test.mp4"),
        created_at=datetime.now(),
        status=UploadStatus.PENDING,
    )
    manager.insert_video(video)

    # Cleanup
    manager.cleanup()

    # Should be able to create new manager with same database
    manager2 = MetadataManager(temp_storage_dir)
    videos = manager2.list_videos()
    assert len(videos) == 1

    manager2.cleanup()


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


@pytest.mark.unit_integration
def test_complete_video_lifecycle(temp_storage_dir):
    """
    Integration test: Complete video lifecycle in database.
    """
    manager = MetadataManager(temp_storage_dir)

    # Create and insert
    video = VideoFile(
        filename="lifecycle.mp4",
        filepath=Path("/fake/pending/lifecycle.mp4"),
        created_at=datetime.now(),
        status=UploadStatus.PENDING,
    )
    video = manager.insert_video(video)
    assert video.id is not None

    # Mark as in progress
    video.status = UploadStatus.IN_PROGRESS
    manager.update_video(video)

    # Mark as completed
    video.status = UploadStatus.COMPLETED
    video.youtube_url = "https://youtube.com/test"
    manager.update_video(video)

    # Verify final state
    retrieved = manager.get_video(video.id)
    assert retrieved.status == UploadStatus.COMPLETED
    assert retrieved.youtube_url == "https://youtube.com/test"

    # Delete
    manager.delete_video(video.id)

    # Verify deleted
    assert manager.get_video(video.id) is None

    manager.cleanup()
