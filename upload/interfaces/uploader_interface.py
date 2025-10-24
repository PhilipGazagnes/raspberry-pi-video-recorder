"""
Uploader Interface

Abstract interface for video upload implementations.
Follows Dependency Inversion Principle - high-level code depends on this abstraction,
not on concrete YouTube API implementation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from upload.constants import UploadStatus


@dataclass
class UploadResult:
    """
    Result of an upload operation.

    Attributes:
        success: True if upload completed successfully
        video_id: YouTube video ID (if successful)
        status: Upload status code
        error_message: Error description (if failed)
        upload_duration: Time taken to upload in seconds
        file_size: Size of uploaded file in bytes
    """

    success: bool
    video_id: Optional[str] = None
    status: UploadStatus = UploadStatus.SUCCESS
    error_message: Optional[str] = None
    upload_duration: float = 0.0
    file_size: int = 0


class UploaderInterface(ABC):
    """
    Abstract base class for video uploaders.

    Any uploader implementation (YouTube, Vimeo, local storage, etc.)
    must implement these methods.
    """

    @abstractmethod
    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        playlist_id: Optional[str] = None,
    ) -> UploadResult:
        """
        Upload a video file.

        This is the main upload method. It should handle:
        - File validation
        - Authentication
        - Upload progress
        - Error handling

        Args:
            video_path: Path to video file to upload
            title: Video title
            description: Video description (optional)
            tags: List of tags (optional)
            playlist_id: Add to this playlist (optional)

        Returns:
            UploadResult with success status and details

        Example:
            result = uploader.upload_video(
                video_path="/path/to/video.mp4",
                title="Boxing Session 2025-10-12 18:30:45",
                playlist_id="PLxxxxxxxxxx"
            )
        """

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if uploader is ready to upload.

        Returns:
            True if authentication is valid and service is accessible

        Example:
            if uploader.is_available():
                result = uploader.upload_video(...)
        """

    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test connection to upload service.

        Verifies authentication and network connectivity without uploading.

        Returns:
            True if connection successful

        Example:
            if not uploader.test_connection():
                print("Cannot connect to YouTube")
        """

    @abstractmethod
    def get_upload_quota_remaining(self) -> Optional[int]:
        """
        Get remaining upload quota (if applicable).

        YouTube has daily upload quotas. This helps detect quota issues.

        Returns:
            Remaining quota units, or None if not applicable/unknown

        Example:
            quota = uploader.get_upload_quota_remaining()
            if quota and quota < 1000:
                print("Warning: Low upload quota")
        """


class UploaderError(Exception):
    """
    Exception raised for upload-related errors.

    Examples:
    - Authentication failed
    - Network error
    - Invalid video file
    - API quota exceeded
    """

    def __init__(self, message: str, status: UploadStatus = UploadStatus.FAILED):
        super().__init__(message)
        self.status = status
