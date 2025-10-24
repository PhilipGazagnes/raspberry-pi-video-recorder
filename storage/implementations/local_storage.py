"""
Local Storage Implementation

Concrete implementation of StorageInterface using local filesystem.
Coordinates all managers to provide complete storage functionality.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from config import settings
from config.settings import (
    DIR_CORRUPTED,
    DIR_FAILED,
    DIR_PENDING,
    DIR_UPLOADED,
)
from storage.constants import UploadStatus, VideoQuality
from storage.interfaces.storage_interface import StorageError, StorageInterface
from storage.managers.cleanup_manager import CleanupManager
from storage.managers.file_manager import FileManager
from storage.managers.metadata_manager import MetadataManager
from storage.managers.space_manager import SpaceManager
from storage.models.video_file import StorageStats, VideoFile
from storage.utils.validation_utils import (
    get_video_duration,
    validate_video_file,
)


class LocalStorage(StorageInterface):
    """
    Local filesystem storage implementation.

    This class coordinates all managers to provide complete storage functionality.
    It's the "real" storage that actually saves files and manages metadata.
    """

    def __init__(self):
        """
        Initialize local storage.

        Configuration is loaded from config.settings (central config).
        """
        self.logger = logging.getLogger(__name__)

        # Initialize managers (all now use config.settings internally)
        self.file_manager = FileManager(settings.STORAGE_BASE_PATH)
        self.metadata_manager = MetadataManager(settings.STORAGE_BASE_PATH)
        self.space_manager = SpaceManager(settings.STORAGE_BASE_PATH)
        self.cleanup_manager = CleanupManager()

        # Last cleanup timestamp (for auto-cleanup)
        self._last_cleanup = datetime.now()

        self.logger.info(
            f"Local storage initialized (base: {settings.STORAGE_BASE_PATH})",
        )

    def initialize(self) -> None:
        """Initialize storage system (directories already created by FileManager)"""
        # Verify storage is writable
        if not self.file_manager.validate_storage_writable():
            raise StorageError("Storage directory is not writable")

        self.logger.info("Storage system initialized and ready")

    def save_video(
        self,
        source_path: Path,
        duration_seconds: Optional[int] = None,
    ) -> VideoFile:
        """
        Save a new video file to storage.

        Process:
        1. Check disk space
        2. Generate filename and save to pending/
        3. Validate file integrity
        4. Get file size and duration
        5. Create metadata entry

        Args:
            source_path: Path to video file to save
            duration_seconds: Video duration (auto-detected if None)

        Returns:
            VideoFile object with metadata

        Raises:
            StorageError: If save fails
        """
        # Check space available
        if not self.space_manager.check_space_available():
            raise StorageError("Insufficient disk space for video")

        try:
            # Save file to pending directory
            dest_path = self.file_manager.save_file(
                source_path,
                destination_dir=DIR_PENDING,
            )

            self.logger.info(f"Saved video file: {dest_path.name}")

            # Get file info
            file_size = self.file_manager.get_file_size(dest_path)

            # Get duration (from parameter or detect)
            if duration_seconds is None:
                duration_seconds = get_video_duration(dest_path)

            # Create VideoFile object
            video = VideoFile(
                filename=dest_path.name,
                filepath=dest_path,
                created_at=datetime.now(),
                duration_seconds=duration_seconds,
                file_size_bytes=file_size,
                status=UploadStatus.PENDING,
            )

            # Validate video
            if settings.ENABLE_FFMPEG_VALIDATION:
                is_valid = self.validate_video(video)
                if not is_valid:
                    # Video was marked corrupted and moved
                    raise StorageError(
                        f"Video validation failed: {video.validation_error}",
                    )

            # Save metadata to database
            video = self.metadata_manager.insert_video(video)

            self.logger.info(
                f"Video saved successfully: {video.filename} "
                f"(id={video.id}, size={file_size/(1024**2):.2f}MB)",
            )

            return video

        except Exception as e:
            # Clean up on error
            if dest_path and dest_path.exists():
                try:
                    self.file_manager.delete_file(dest_path)
                except:
                    pass
            raise StorageError(f"Failed to save video: {e}") from e

    def get_video(self, video_id: int) -> Optional[VideoFile]:
        """Get video by ID"""
        return self.metadata_manager.get_video(video_id)

    def get_video_by_filename(self, filename: str) -> Optional[VideoFile]:
        """Get video by filename"""
        return self.metadata_manager.get_video_by_filename(filename)

    def list_videos(
        self,
        status: Optional[UploadStatus] = None,
        limit: Optional[int] = None,
    ) -> List[VideoFile]:
        """List videos with optional filtering"""
        return self.metadata_manager.list_videos(status=status, limit=limit)

    def update_video(self, video: VideoFile) -> None:
        """Update video metadata"""
        self.metadata_manager.update_video(video)
        self.logger.debug(f"Updated video: {video.filename}")

    def delete_video(self, video: VideoFile, remove_file: bool = True) -> None:
        """
        Delete video from storage.

        Args:
            video: VideoFile to delete
            remove_file: If True, also delete physical file
        """
        try:
            # Delete from database
            if video.id:
                self.metadata_manager.delete_video(video.id)

            # Delete physical file
            if remove_file and video.exists:
                self.file_manager.delete_file(video.filepath)

            self.logger.info(f"Deleted video: {video.filename}")

        except Exception as e:
            raise StorageError(f"Failed to delete video: {e}") from e

    def move_video(self, video: VideoFile, destination_dir: str) -> VideoFile:
        """
        Move video to different directory.

        Args:
            video: VideoFile to move
            destination_dir: Target directory (uploaded/failed/corrupted)

        Returns:
            Updated VideoFile with new path
        """
        try:
            # Move physical file
            new_path = self.file_manager.move_file(
                video.filepath,
                destination_dir,
            )

            # Update video object
            video.filepath = new_path

            # Update status based on destination
            if destination_dir == DIR_UPLOADED:
                if video.status != UploadStatus.COMPLETED:
                    video.status = UploadStatus.COMPLETED
            elif destination_dir == DIR_FAILED:
                if video.status != UploadStatus.FAILED:
                    video.status = UploadStatus.FAILED
            elif destination_dir == DIR_CORRUPTED:
                video.status = UploadStatus.CORRUPTED

            # Update metadata
            self.update_video(video)

            self.logger.info(
                f"Moved video: {video.filename} -> {destination_dir}/",
            )

            return video

        except Exception as e:
            raise StorageError(f"Failed to move video: {e}") from e

    def validate_video(self, video: VideoFile) -> bool:
        """
        Validate video file integrity.

        If validation fails, video is automatically moved to corrupted/

        Args:
            video: VideoFile to validate

        Returns:
            True if valid, False if corrupted
        """
        quality, error = validate_video_file(
            video.filepath,
            enable_ffmpeg=settings.ENABLE_FFMPEG_VALIDATION,
            min_size=settings.MIN_VIDEO_SIZE_BYTES,
        )

        if quality != VideoQuality.VALID:
            # Mark as corrupted
            video.mark_corrupted(error or "Validation failed")

            # Move to corrupted directory
            try:
                self.move_video(video, DIR_CORRUPTED)
            except Exception as e:
                self.logger.error(f"Failed to move corrupted video: {e}")

            self.logger.error(
                f"Video validation failed: {video.filename} - {error}",
            )
            return False

        self.logger.debug(f"Video validated successfully: {video.filename}")
        return True

    def get_stats(self) -> StorageStats:
        """Get storage system statistics"""
        try:
            # Get disk usage
            total, used, free = self.space_manager.get_disk_usage()

            # Get video counts by status
            counts = self.metadata_manager.get_count_by_status()
            total_videos = self.metadata_manager.get_total_count()

            # Calculate total video size (from all directories)
            total_size = sum(
                self.file_manager.get_directory_size(dir_name)
                for dir_name in [DIR_PENDING, DIR_UPLOADED, DIR_FAILED, DIR_CORRUPTED]
            )

            return StorageStats(
                total_space_bytes=total,
                used_space_bytes=used,
                free_space_bytes=free,
                pending_count=counts.get(UploadStatus.PENDING.value, 0),
                in_progress_count=counts.get(UploadStatus.IN_PROGRESS.value, 0),
                completed_count=counts.get(UploadStatus.COMPLETED.value, 0),
                failed_count=counts.get(UploadStatus.FAILED.value, 0),
                corrupted_count=counts.get(UploadStatus.CORRUPTED.value, 0),
                total_videos=total_videos,
                total_size_bytes=total_size,
            )

        except Exception as e:
            raise StorageError(f"Failed to get storage stats: {e}") from e

    def check_space_available(self) -> bool:
        """Check if enough space for recording"""
        return self.space_manager.check_space_available()

    def cleanup_old_videos(self, dry_run: bool = False) -> int:
        """
        Clean up old uploaded videos.

        Args:
            dry_run: If True, only simulate without deleting

        Returns:
            Number of videos cleaned up
        """
        try:
            # Get all uploaded videos
            uploaded_videos = self.list_videos(status=UploadStatus.COMPLETED)

            # Plan cleanup
            to_cleanup, plan_stats = self.cleanup_manager.plan_cleanup(
                uploaded_videos,
            )

            if not to_cleanup:
                self.logger.info("No videos need cleanup")
                return 0

            # Execute cleanup
            cleanup_stats = self.cleanup_manager.cleanup_videos(
                to_cleanup,
                delete_func=lambda v: self.delete_video(v, remove_file=True),
                dry_run=dry_run,
            )

            # Update last cleanup time
            if not dry_run:
                self._last_cleanup = datetime.now()

            return cleanup_stats["deleted"]

        except Exception as e:
            raise StorageError(f"Cleanup failed: {e}") from e

    def get_retry_queue(self) -> List[VideoFile]:
        """Get videos eligible for upload retry"""
        return self.metadata_manager.get_retry_queue()

    def is_available(self) -> bool:
        """Check if storage system is available"""
        try:
            return (
                settings.STORAGE_BASE_PATH.exists()
                and self.file_manager.validate_storage_writable()
            )
        except Exception:
            return False

    def cleanup(self) -> None:
        """Clean up resources"""
        self.logger.info("Cleaning up local storage")
        self.metadata_manager.cleanup()
        self.logger.info("Local storage cleanup complete")

    def __del__(self):
        """Destructor - ensure cleanup"""
        self.cleanup()
