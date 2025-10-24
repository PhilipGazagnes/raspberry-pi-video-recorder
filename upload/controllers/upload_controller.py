"""
Upload Controller

High-level coordinator for video uploads.
Simplifies upload operations for the main service.

This follows the same pattern as hardware/controllers/audio_controller.py
- Clean, simple API for main service
- Handles all upload complexity internally
- Proper error handling and logging
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from upload.constants import VIDEO_TITLE_PREFIX
from upload.factory import create_uploader
from upload.interfaces.uploader_interface import UploaderInterface, UploadResult


class UploadController:
    """
    High-level video upload controller.

    This class:
    - Provides simple upload API for main service
    - Formats video metadata (title, timestamp)
    - Handles uploader initialization
    - Provides connection testing

    Usage:
        controller = UploadController()

        # Upload video
        result = controller.upload_video(
            video_path="/path/to/video.mp4",
            timestamp="2025-10-12 18:30:45"
        )

        if result.success:
            print(f"Uploaded: {result.video_id}")
    """

    def __init__(
        self,
        uploader: Optional[UploaderInterface] = None,
        playlist_id: Optional[str] = None,
    ):
        """
        Initialize upload controller.

        Args:
            uploader: UploaderInterface implementation, or None to auto-create
            playlist_id: Default playlist for uploads (can be overridden per upload)

        Example:
            # Normal usage - auto-creates from .env
            controller = UploadController()

            # Custom uploader (testing)
            mock = MockUploader()
            controller = UploadController(uploader=mock)
        """
        self.logger = logging.getLogger(__name__)

        # Create or use provided uploader
        self.uploader = uploader or create_uploader()
        self.default_playlist_id = playlist_id

        # Verify uploader is ready
        if not self.uploader.is_available():
            self.logger.warning(
                "Uploader initialized but not available. "
                "Check authentication and network connection.",
            )

        self.logger.info("Upload Controller initialized")

    def upload_video(
        self,
        video_path: str,
        timestamp: str,
        playlist_id: Optional[str] = None,
    ) -> UploadResult:
        """
        Upload video with automatic metadata formatting.

        This is the main method for the service to call.
        Handles all formatting and delegates to uploader.

        Args:
            video_path: Path to video file
            timestamp: Recording timestamp (format: "YYYY-MM-DD HH:MM:SS")
            playlist_id: Override default playlist (optional)

        Returns:
            UploadResult with success status and details

        Example:
            result = controller.upload_video(
                video_path="/recordings/2025-10-12_18-30-45.mp4",
                timestamp="2025-10-12 18:30:45"
            )

            if result.success:
                storage.mark_uploaded(video_path, result.video_id)
            else:
                logger.error(f"Upload failed: {result.error_message}")
        """
        # Format video title
        title = self._format_video_title(timestamp)

        # Determine playlist
        target_playlist = playlist_id or self.default_playlist_id

        self.logger.info(f"Uploading video: {video_path}")
        self.logger.debug(f"Title: {title}, Playlist: {target_playlist}")

        # Delegate to uploader
        result = self.uploader.upload_video(
            video_path=video_path,
            title=title,
            description="",  # No description as per requirements
            tags=None,  # Use default tags from constants
            playlist_id=target_playlist,
        )

        # Log result
        if result.success:
            self.logger.info(
                f"✅ Upload successful: {result.video_id} "
                f"({result.upload_duration:.1f}s, "
                f"{result.file_size / (1024 * 1024):.1f} MB)",
            )
        else:
            self.logger.error(
                f"❌ Upload failed: {result.error_message} "
                f"(status: {result.status.value})",
            )

        return result

    def _format_video_title(self, timestamp: str) -> str:
        """
        Format video title from timestamp.

        Args:
            timestamp: Timestamp string (format: "YYYY-MM-DD HH:MM:SS")

        Returns:
            Formatted title: "{SESSION_TITLE_PREFIX} YYYY-MM-DD HH:MM:SS"

        Example:
            _format_video_title("2025-10-12 18:30:45")
            # Returns: "Video Session 2025-10-12 18:30:45"
            # (customize SESSION_TITLE_PREFIX in config.settings)
        """
        try:
            # Validate timestamp format
            datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            return f"{VIDEO_TITLE_PREFIX} {timestamp}"

        except ValueError:
            # Invalid format - use as-is with warning
            self.logger.warning(
                f"Invalid timestamp format: {timestamp}. "
                f"Expected: YYYY-MM-DD HH:MM:SS",
            )
            return f"{VIDEO_TITLE_PREFIX} {timestamp}"

    def test_connection(self) -> bool:
        """
        Test connection to YouTube API.

        Use this before uploading to verify system is ready.

        Returns:
            True if connection successful

        Example:
            if not controller.test_connection():
                print("Cannot connect to YouTube. Check network and auth.")
        """
        self.logger.info("Testing YouTube connection...")

        try:
            result = self.uploader.test_connection()

            if result:
                self.logger.info("✅ Connection test passed")
            else:
                self.logger.warning("❌ Connection test failed")

            return result

        except Exception as e:
            self.logger.error(f"Connection test error: {e}")
            return False

    def is_ready(self) -> bool:
        """
        Check if uploader is ready to upload.

        Returns:
            True if authenticated and ready

        Example:
            if controller.is_ready():
                result = controller.upload_video(...)
        """
        return self.uploader.is_available()

    def get_status(self) -> Dict[str, Any]:
        """
        Get current controller status.

        Returns:
            Dictionary with status information

        Example:
            status = controller.get_status()
            print(f"Ready: {status['ready']}")
            print(f"Playlist: {status['playlist_id']}")
        """
        return {
            "ready": self.is_ready(),
            "playlist_id": self.default_playlist_id,
            "uploader_type": type(self.uploader).__name__,
        }

    def set_default_playlist(self, playlist_id: str) -> None:
        """
        Change default playlist for future uploads.

        Args:
            playlist_id: YouTube playlist ID

        Example:
            controller.set_default_playlist("PLxxxxxxxxxx")
        """
        self.default_playlist_id = playlist_id
        self.logger.info(f"Default playlist set to: {playlist_id}")

    def cleanup(self) -> None:
        """
        Clean up resources.

        Currently no cleanup needed, but provided for consistency
        with hardware module pattern.
        """
        self.logger.info("Upload Controller cleanup")
