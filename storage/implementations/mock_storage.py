"""
Mock Storage Implementation

In-memory storage implementation for testing without filesystem.
Simulates all storage operations without actually writing files.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from storage.constants import DIR_PENDING, UploadStatus
from storage.interfaces.storage_interface import StorageError, StorageInterface
from storage.models.video_file import StorageStats, VideoFile


class MockStorage(StorageInterface):
    """
    Mock storage for testing.

    This simulates storage operations in memory without touching the filesystem.
    Perfect for unit tests that don't need real file I/O.
    """

    def __init__(
        self,
        simulated_space_bytes: int = 100 * 1024**3,  # 100 GB default
        min_space_bytes: int = 5 * 1024**3,  # 5 GB default
    ):
        """
        Initialize mock storage.

        Args:
            simulated_space_bytes: Fake total disk space
            min_space_bytes: Minimum free space threshold
        """
        self.logger = logging.getLogger(__name__)

        # In-memory video storage (id -> VideoFile)
        self._videos: Dict[int, VideoFile] = {}
        self._next_id = 1

        # Simulated disk space
        self._total_space = simulated_space_bytes
        self._used_space = 0
        self._min_space = min_space_bytes

        # Track operations for test verification
        self.operation_log: List[str] = []

        self.logger.info("[MOCK] Storage initialized (simulation mode)")

    def _log_operation(self, operation: str) -> None:
        """Log operation for test verification"""
        self.operation_log.append(operation)
        self.logger.debug(f"[MOCK] {operation}")

    def initialize(self) -> None:
        """Initialize mock storage"""
        self._log_operation("initialize")

    def save_video(
        self,
        source_path: Path,
        duration_seconds: Optional[int] = None,
    ) -> VideoFile:
        """
        Save video (simulated - doesn't actually copy file).

        Args:
            source_path: Path to source (not actually read)
            duration_seconds: Video duration

        Returns:
            VideoFile object
        """
        # Check space
        if not self.check_space_available():
            raise StorageError("Insufficient disk space (simulated)")

        # Create VideoFile
        filename = f"recording_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.mp4"
        filepath = Path("/mock/storage") / DIR_PENDING / filename

        # Simulate file size (100 MB default)
        file_size = 100 * 1024 * 1024

        video = VideoFile(
            id=self._next_id,
            filename=filename,
            filepath=filepath,
            created_at=datetime.now(),
            duration_seconds=duration_seconds or 600,  # 10 min default
            file_size_bytes=file_size,
            status=UploadStatus.PENDING,
        )

        # Store in memory
        self._videos[self._next_id] = video
        self._next_id += 1

        # Update simulated space usage
        self._used_space += file_size

        self._log_operation(f"save_video: {filename}")
        return video

    def get_video(self, video_id: int) -> Optional[VideoFile]:
        """Get video by ID"""
        return self._videos.get(video_id)

    def get_video_by_filename(self, filename: str) -> Optional[VideoFile]:
        """Get video by filename"""
        for video in self._videos.values():
            if video.filename == filename:
                return video
        return None

    def list_videos(
        self,
        status: Optional[UploadStatus] = None,
        limit: Optional[int] = None,
    ) -> List[VideoFile]:
        """List videos with optional filtering"""
        videos = list(self._videos.values())

        if status:
            videos = [v for v in videos if v.status == status]

        # Sort by creation date (newest first)
        videos.sort(key=lambda v: v.created_at, reverse=True)

        if limit:
            videos = videos[:limit]

        return videos

    def update_video(self, video: VideoFile) -> None:
        """Update video metadata"""
        if video.id not in self._videos:
            raise StorageError(f"Video not found: id={video.id}")

        self._videos[video.id] = video
        self._log_operation(f"update_video: {video.filename}")

    def delete_video(self, video: VideoFile, remove_file: bool = True) -> None:
        """Delete video from mock storage"""
        if video.id and video.id in self._videos:
            # Update space usage
            if video.file_size_bytes:
                self._used_space -= video.file_size_bytes

            del self._videos[video.id]
            self._log_operation(f"delete_video: {video.filename}")

    def move_video(self, video: VideoFile, destination_dir: str) -> VideoFile:
        """Move video to different directory (simulated)"""
        # Just update the path
        video.filepath = Path("/mock/storage") / destination_dir / video.filename

        # Update status based on directory
        if destination_dir == "uploaded":
            video.status = UploadStatus.COMPLETED
        elif destination_dir == "failed":
            video.status = UploadStatus.FAILED
        elif destination_dir == "corrupted":
            video.status = UploadStatus.CORRUPTED

        self.update_video(video)
        self._log_operation(f"move_video: {video.filename} -> {destination_dir}")
        return video

    def validate_video(self, video: VideoFile) -> bool:
        """Mock validation always succeeds"""
        self._log_operation(f"validate_video: {video.filename}")
        return True

    def get_stats(self) -> StorageStats:
        """Get simulated storage statistics"""
        # Count by status
        counts = {}
        for video in self._videos.values():
            status_val = video.status.value
            counts[status_val] = counts.get(status_val, 0) + 1

        return StorageStats(
            total_space_bytes=self._total_space,
            used_space_bytes=self._used_space,
            free_space_bytes=self._total_space - self._used_space,
            pending_count=counts.get(UploadStatus.PENDING.value, 0),
            in_progress_count=counts.get(UploadStatus.IN_PROGRESS.value, 0),
            completed_count=counts.get(UploadStatus.COMPLETED.value, 0),
            failed_count=counts.get(UploadStatus.FAILED.value, 0),
            corrupted_count=counts.get(UploadStatus.CORRUPTED.value, 0),
            total_videos=len(self._videos),
            total_size_bytes=self._used_space,
        )

    def check_space_available(self) -> bool:
        """Check if simulated space is available"""
        free_space = self._total_space - self._used_space
        return free_space >= self._min_space

    def cleanup_old_videos(self, dry_run: bool = False) -> int:
        """Mock cleanup - removes oldest completed videos"""
        completed = [v for v in self._videos.values() if v.is_completed]

        # Sort by age
        completed.sort(key=lambda v: v.created_at)

        # Remove oldest 5
        to_remove = completed[:5] if len(completed) > 5 else []

        if not dry_run:
            for video in to_remove:
                self.delete_video(video)

        self._log_operation(f"cleanup_old_videos: {len(to_remove)} videos")
        return len(to_remove)

    def get_retry_queue(self) -> List[VideoFile]:
        """Get failed videos that can be retried"""
        return [v for v in self._videos.values() if v.is_failed and v.can_retry]

    def is_available(self) -> bool:
        """Mock storage is always available"""
        return True

    def cleanup(self) -> None:
        """Clean up mock storage"""
        self._log_operation("cleanup")

    # =========================================================================
    # TESTING HELPER METHODS
    # =========================================================================

    def simulate_disk_full(self) -> None:
        """Simulate disk full condition for testing"""
        self._used_space = self._total_space - (self._min_space - 1)
        self._log_operation("simulate_disk_full")

    def simulate_low_space(self) -> None:
        """Simulate low space warning for testing"""
        # Set space just above minimum
        self._used_space = self._total_space - (self._min_space + 1024**3)
        self._log_operation("simulate_low_space")

    def add_fake_video(
        self,
        filename: str,
        status: UploadStatus = UploadStatus.PENDING,
    ) -> VideoFile:
        """Add a fake video for testing"""
        video = VideoFile(
            id=self._next_id,
            filename=filename,
            filepath=Path(f"/mock/{status.value}/{filename}"),
            created_at=datetime.now(),
            duration_seconds=600,
            file_size_bytes=100 * 1024 * 1024,
            status=status,
        )

        self._videos[self._next_id] = video
        self._next_id += 1
        self._used_space += video.file_size_bytes

        return video

    def get_operation_log(self) -> List[str]:
        """Get list of all operations for test verification"""
        return self.operation_log.copy()

    def clear_operation_log(self) -> None:
        """Clear operation log"""
        self.operation_log.clear()

    def reset(self) -> None:
        """Reset mock storage to initial state"""
        self._videos.clear()
        self._next_id = 1
        self._used_space = 0
        self.operation_log.clear()
        self._log_operation("reset")
