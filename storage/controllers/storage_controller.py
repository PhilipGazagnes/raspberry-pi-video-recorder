"""
Storage Controller

High-level storage coordination following the same pattern as hardware controllers.
Provides simple API with event callbacks for the main application.
"""

import logging
from pathlib import Path
from typing import Callable, List, Optional

from config import settings
from config.settings import DIR_FAILED, DIR_UPLOADED
from storage.constants import UploadStatus
from storage.implementations.local_storage import LocalStorage
from storage.interfaces.storage_interface import StorageError, StorageInterface
from storage.models.video_file import StorageStats, VideoFile


class StorageController:
    """
    High-level storage controller.

    This class:
    - Provides simple API for video storage operations
    - Coordinates storage implementation
    - Fires events for important conditions
    - Manages automatic cleanup

    Usage:
        storage = StorageController()
        storage.on_disk_full = lambda: handle_disk_full()
        storage.on_low_space = lambda bytes: handle_low_space(bytes)

        video = storage.save_recording("/path/to/video.mp4")
        storage.mark_upload_success(video, "https://youtube.com/...")
    """

    def __init__(
        self,
        storage_impl: Optional[StorageInterface] = None,
    ):
        """
        Initialize storage controller.

        Args:
            storage_impl: Storage implementation (None = auto-create LocalStorage)
        """
        self.logger = logging.getLogger(__name__)

        # Storage implementation
        self.storage = storage_impl or LocalStorage()
        self.storage.initialize()

        # Event callbacks (like hardware controllers)
        self.on_disk_full: Optional[Callable[[], None]] = None
        self.on_low_space: Optional[Callable[[int], None]] = None  # passes free bytes
        self.on_corruption_detected: Optional[Callable[[str], None]] = (
            None  # passes filename
        )
        self.on_cleanup_complete: Optional[Callable[[int], None]] = None  # passes count
        self.on_storage_error: Optional[Callable[[str], None]] = (
            None  # passes error message
        )

        self.logger.info("Storage controller initialized")

    # =========================================================================
    # VIDEO OPERATIONS
    # =========================================================================

    def save_recording(
        self,
        video_path: Path,
        duration_seconds: Optional[int] = None,
    ) -> Optional[VideoFile]:
        """
        Save a new recording to storage.

        Args:
            video_path: Path to recorded video file
            duration_seconds: Video duration in seconds

        Returns:
            VideoFile object, or None if save failed

        Example:
            video = storage.save_recording("/tmp/recording.mp4", 600)
            if video:
                print(f"Saved: {video.filename}")
        """
        # Check space first
        if not self.check_space():
            self.logger.error("Cannot save recording: insufficient disk space")
            self._trigger_disk_full()
            return None

        try:
            video = self.storage.save_video(video_path, duration_seconds)

            # Calculate file size, handle None case
            file_size_mb = (
                (video.file_size_bytes / (1024**2)) if video.file_size_bytes else 0.0
            )
            self.logger.info(
                f"Recording saved: {video.filename} ({file_size_mb:.2f} MB)",
            )

            # Check space after save
            self._check_space_warnings()

            return video

        except StorageError as e:
            self.logger.error(f"Failed to save recording: {e}")
            self._trigger_error(str(e))
            return None

    def mark_upload_started(self, video: VideoFile) -> bool:
        """
        Mark video upload as started.

        Args:
            video: VideoFile being uploaded

        Returns:
            True if successful
        """
        try:
            video.mark_upload_started()
            self.storage.update_video(video)

            self.logger.info(f"Upload started: {video.filename}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to mark upload started: {e}")
            return False

    def mark_upload_success(self, video: VideoFile, youtube_url: str) -> bool:
        """
        Mark video upload as successful.

        Moves video to uploaded/ directory.

        Args:
            video: VideoFile that was uploaded
            youtube_url: URL of uploaded video

        Returns:
            True if successful
        """
        try:
            video.mark_upload_success(youtube_url)

            # Move to uploaded directory
            video = self.storage.move_video(video, DIR_UPLOADED)

            self.logger.info(
                f"Upload successful: {video.filename} -> {youtube_url}",
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to mark upload success: {e}")
            return False

    def mark_upload_failed(self, video: VideoFile, error: str) -> bool:
        """
        Mark video upload as failed.

        Moves video to failed/ directory for retry.

        Args:
            video: VideoFile that failed to upload
            error: Error message

        Returns:
            True if successful
        """
        try:
            video.mark_upload_failed(error)

            # Move to failed directory
            video = self.storage.move_video(video, DIR_FAILED)

            self.logger.warning(
                f"Upload failed: {video.filename} "
                f"(attempt {video.upload_attempts}): {error}",
            )

            # Check if exceeded retry limit
            if not video.can_retry:
                self.logger.error(
                    f"Video exceeded retry limit: {video.filename} "
                    f"({video.upload_attempts} attempts)",
                )

            return True

        except Exception as e:
            self.logger.error(f"Failed to mark upload failed: {e}")
            return False

    def get_pending_uploads(self) -> List[VideoFile]:
        """
        Get all videos pending upload.

        Returns:
            List of pending VideoFile objects
        """
        return self.storage.list_videos(status=UploadStatus.PENDING)

    def get_retry_queue(self) -> List[VideoFile]:
        """
        Get videos that need upload retry.

        Returns:
            List of failed videos eligible for retry
        """
        return self.storage.get_retry_queue()

    def get_video_by_filename(self, filename: str) -> Optional[VideoFile]:
        """Get video by filename"""
        return self.storage.get_video_by_filename(filename)

    # =========================================================================
    # SPACE MANAGEMENT
    # =========================================================================

    def check_space(self) -> bool:
        """
        Check if enough disk space for recording.

        Returns:
            True if space available, False if disk full
        """
        return self.storage.check_space_available()

    def get_stats(self) -> StorageStats:
        """
        Get storage statistics.

        Returns:
            StorageStats object with disk and video info
        """
        return self.storage.get_stats()

    def _check_space_warnings(self) -> None:
        """Check space and fire appropriate warnings"""
        stats = self.get_stats()

        if stats.is_disk_full:
            self._trigger_disk_full()
        elif stats.is_low_space:
            self._trigger_low_space(stats.free_space_bytes)

    # =========================================================================
    # CLEANUP OPERATIONS
    # =========================================================================

    def cleanup_old_videos(self, dry_run: bool = False) -> int:
        """
        Clean up old uploaded videos.

        Args:
            dry_run: If True, only simulate without deleting

        Returns:
            Number of videos cleaned up
        """
        try:
            count = self.storage.cleanup_old_videos(dry_run)

            if count > 0:
                if dry_run:
                    self.logger.info(f"Would cleanup {count} old videos")
                else:
                    self.logger.info(f"Cleaned up {count} old videos")
                    self._trigger_cleanup_complete(count)

            return count

        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            self._trigger_error(f"Cleanup failed: {e}")
            return 0

    def get_cleanup_summary(self) -> dict:
        """
        Get summary of what would be cleaned up.

        Returns:
            Dictionary with cleanup information
        """
        try:
            # Get all uploaded videos
            uploaded = self.storage.list_videos(status=UploadStatus.COMPLETED)

            # Use cleanup manager through storage
            from storage.managers.cleanup_manager import CleanupManager

            cleanup_mgr = CleanupManager()

            return cleanup_mgr.get_cleanup_summary(uploaded)

        except Exception as e:
            self.logger.error(f"Failed to get cleanup summary: {e}")
            return {}

    # =========================================================================
    # STATUS AND DIAGNOSTICS
    # =========================================================================

    def get_status(self) -> dict:
        """
        Get comprehensive storage status.

        Returns:
            Dictionary with all status information
        """
        stats = self.get_stats()

        return {
            "available": self.storage.is_available(),
            "storage_stats": stats.to_dict(),
            "pending_uploads": len(self.get_pending_uploads()),
            "retry_queue_size": len(self.get_retry_queue()),
            "can_record": self.check_space(),
            "config": {
                "base_path": str(settings.STORAGE_BASE_PATH),
                "min_free_space_gb": settings.MIN_FREE_SPACE_BYTES / (1024**3),
                "retention_days": settings.UPLOADED_RETENTION_DAYS,
                "max_uploaded_videos": settings.MAX_UPLOADED_VIDEOS,
            },
        }

    def log_status(self) -> None:
        """Log current storage status"""
        stats = self.get_stats()

        self.logger.info(
            f"Storage Status: "
            f"Free={stats.free_space_gb:.2f}GB, "
            f"Videos={stats.total_videos} "
            f"(pending={stats.pending_count}, "
            f"completed={stats.completed_count}, "
            f"failed={stats.failed_count})",
        )

    # =========================================================================
    # EVENT TRIGGERS
    # =========================================================================

    def _trigger_disk_full(self) -> None:
        """Trigger disk full event"""
        if self.on_disk_full:
            try:
                self.on_disk_full()
            except Exception as e:
                self.logger.error(f"Error in disk_full callback: {e}")

    def _trigger_low_space(self, free_bytes: int) -> None:
        """Trigger low space warning event"""
        if self.on_low_space:
            try:
                self.on_low_space(free_bytes)
            except Exception as e:
                self.logger.error(f"Error in low_space callback: {e}")

    def _trigger_corruption_detected(self, filename: str) -> None:
        """Trigger corruption detected event"""
        if self.on_corruption_detected:
            try:
                self.on_corruption_detected(filename)
            except Exception as e:
                self.logger.error(f"Error in corruption_detected callback: {e}")

    def _trigger_cleanup_complete(self, count: int) -> None:
        """Trigger cleanup complete event"""
        if self.on_cleanup_complete:
            try:
                self.on_cleanup_complete(count)
            except Exception as e:
                self.logger.error(f"Error in cleanup_complete callback: {e}")

    def _trigger_error(self, error_msg: str) -> None:
        """Trigger storage error event"""
        if self.on_storage_error:
            try:
                self.on_storage_error(error_msg)
            except Exception as e:
                self.logger.error(f"Error in storage_error callback: {e}")

    # =========================================================================
    # CLEANUP
    # =========================================================================

    def cleanup(self) -> None:
        """Clean up storage resources"""
        self.logger.info("Cleaning up storage controller")
        self.storage.cleanup()
        self.logger.info("Storage controller cleanup complete")

    def __del__(self):
        """Destructor - ensure cleanup"""
        self.cleanup()
