"""
Storage Interface

Abstract interface for storage operations following Dependency Inversion Principle.
Controllers depend on this interface, not concrete implementations.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from storage.models.video_file import StorageStats, VideoFile

if TYPE_CHECKING:
    from storage.constants import UploadStatus


class StorageInterface(ABC):
    """
    Abstract base class for storage operations.

    Any storage implementation must provide these methods.
    This allows easy swapping between real filesystem storage and mock
    storage for testing.
    """

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize storage system.

        Creates necessary directories, database, etc.

        Raises:
            StorageError: If initialization fails
        """

    @abstractmethod
    def save_video(
        self,
        source_path: Path,
        duration_seconds: Optional[int] = None,
    ) -> VideoFile:
        """
        Save a new video file to storage.

        Args:
            source_path: Path to the video file to save
            duration_seconds: Video duration in seconds (optional)

        Returns:
            VideoFile object with metadata

        Raises:
            StorageError: If save operation fails
        """

    @abstractmethod
    def get_video(self, video_id: int) -> Optional[VideoFile]:
        """
        Retrieve video metadata by ID.

        Args:
            video_id: Database ID of the video

        Returns:
            VideoFile object or None if not found
        """

    @abstractmethod
    def get_video_by_filename(self, filename: str) -> Optional[VideoFile]:
        """
        Retrieve video metadata by filename.

        Args:
            filename: Video filename

        Returns:
            VideoFile object or None if not found
        """

    @abstractmethod
    def list_videos(
        self,
        status: Optional["UploadStatus"] = None,
        limit: Optional[int] = None,
    ) -> List[VideoFile]:
        """
        List videos, optionally filtered by status.

        Args:
            status: Filter by upload status (None = all videos)
            limit: Maximum number of videos to return

        Returns:
            List of VideoFile objects
        """

    @abstractmethod
    def update_video(self, video: VideoFile) -> None:
        """
        Update video metadata in database.

        Args:
            video: VideoFile object with updated data

        Raises:
            StorageError: If update fails
        """

    @abstractmethod
    def delete_video(self, video: VideoFile, remove_file: bool = True) -> None:
        """
        Delete video from storage.

        Args:
            video: VideoFile to delete
            remove_file: If True, also delete the physical file

        Raises:
            StorageError: If deletion fails
        """

    @abstractmethod
    def move_video(self, video: VideoFile, destination_dir: str) -> VideoFile:
        """
        Move video to different directory (pending/uploaded/failed/corrupted).

        Args:
            video: VideoFile to move
            destination_dir: Target directory name (e.g., "uploaded", "failed")

        Returns:
            Updated VideoFile with new path

        Raises:
            StorageError: If move fails
        """

    @abstractmethod
    def validate_video(self, video: VideoFile) -> bool:
        """
        Validate video file integrity.

        Checks file size, format, and readability using ffmpeg.

        Args:
            video: VideoFile to validate

        Returns:
            True if valid, False if corrupted
        """

    @abstractmethod
    def get_stats(self) -> StorageStats:
        """
        Get storage system statistics.

        Returns:
            StorageStats object with disk space and video counts
        """

    @abstractmethod
    def check_space_available(self) -> bool:
        """
        Check if enough disk space is available for recording.

        Returns:
            True if space >= MIN_FREE_SPACE_BYTES, False otherwise
        """

    @abstractmethod
    def cleanup_old_videos(self, dry_run: bool = False) -> int:
        """
        Clean up old uploaded videos according to retention policy.

        Args:
            dry_run: If True, only count files without deleting

        Returns:
            Number of videos cleaned up (or would be cleaned up if dry_run)
        """

    @abstractmethod
    def get_retry_queue(self) -> List[VideoFile]:
        """
        Get list of videos eligible for upload retry.

        Returns:
            List of failed videos that haven't exceeded retry limit
        """

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if storage system is available and functional.

        Returns:
            True if storage is ready, False otherwise
        """

    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up storage resources (close database connections, etc.).
        """


class StorageError(Exception):
    """
    Custom exception for storage-related errors.

    Makes it easy to catch storage-specific errors:
        except StorageError as e:
            logger.error(f"Storage failed: {e}")
    """
