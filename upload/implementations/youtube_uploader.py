"""
YouTube Uploader Implementation

Concrete implementation of UploaderInterface for YouTube API v3.
Handles video uploads with resumable upload protocol.
"""

import logging
import os
import time
from typing import List, Optional

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False

from upload.auth.oauth_manager import OAuthManager
from upload.constants import (
    DEFAULT_PRIVACY_STATUS,
    DEFAULT_VIDEO_TAGS,
    MAX_VIDEO_FILE_SIZE,
    MIN_VIDEO_FILE_SIZE,
    SUPPORTED_VIDEO_FORMATS,
    UPLOAD_CHUNK_SIZE,
    UPLOAD_TIMEOUT,
    YOUTUBE_API_SERVICE_NAME,
    YOUTUBE_API_VERSION,
    YOUTUBE_CATEGORY_SPORTS,
    UploadStatus,
)
from upload.interfaces.uploader_interface import (
    UploaderError,
    UploaderInterface,
    UploadResult,
)


class YouTubeUploader(UploaderInterface):
    """
    YouTube video uploader using YouTube Data API v3.

    Features:
    - Resumable uploads (handles network interruptions)
    - Chunk-based upload (memory efficient)
    - Automatic playlist addition
    - Comprehensive error handling
    """

    def __init__(
        self,
        oauth_manager: OAuthManager,
        playlist_id: Optional[str] = None,
    ):
        """
        Initialize YouTube uploader.

        Args:
            oauth_manager: OAuth manager for authentication
            playlist_id: Default playlist ID for uploads (optional)

        Example:
            oauth = OAuthManager(client_secret_path, token_path)
            uploader = YouTubeUploader(oauth, playlist_id="PLxxxxx")
        """
        self.logger = logging.getLogger(__name__)

        if not GOOGLE_API_AVAILABLE:
            raise ImportError(
                "Google API client not available. "
                "Install with: pip install google-api-python-client",
            )

        self.oauth_manager = oauth_manager
        self.default_playlist_id = playlist_id
        self.youtube_service = None

        # Initialize YouTube service
        self._initialize_service()

        self.logger.info("YouTube Uploader initialized")

    def _initialize_service(self) -> None:
        """
        Initialize YouTube API service with authenticated credentials.

        Raises:
            UploaderError: If service initialization fails
        """
        try:
            credentials = self.oauth_manager.get_credentials()

            self.youtube_service = build(
                YOUTUBE_API_SERVICE_NAME,
                YOUTUBE_API_VERSION,
                credentials=credentials,
            )

            self.logger.debug("YouTube API service initialized")

        except Exception as e:
            raise UploaderError(
                f"Failed to initialize YouTube service: {e}",
                status=UploadStatus.AUTH_ERROR,
            ) from e

    def _validate_video_file(self, video_path: str) -> None:
        """
        Validate video file before upload.

        Args:
            video_path: Path to video file

        Raises:
            UploaderError: If file is invalid
        """
        # Check file exists
        if not os.path.exists(video_path):
            raise UploaderError(
                f"Video file not found: {video_path}",
                status=UploadStatus.INVALID_FILE,
            )

        # Check file extension
        file_ext = os.path.splitext(video_path)[1].lower()
        if file_ext not in SUPPORTED_VIDEO_FORMATS:
            raise UploaderError(
                f"Unsupported video format: {file_ext}. "
                f"Supported: {SUPPORTED_VIDEO_FORMATS}",
                status=UploadStatus.INVALID_FILE,
            )

        # Check file size
        file_size = os.path.getsize(video_path)

        if file_size < MIN_VIDEO_FILE_SIZE:
            raise UploaderError(
                f"Video file too small ({file_size} bytes). "
                f"Minimum: {MIN_VIDEO_FILE_SIZE} bytes. File may be corrupted.",
                status=UploadStatus.INVALID_FILE,
            )

        if file_size > MAX_VIDEO_FILE_SIZE:
            raise UploaderError(
                f"Video file too large ({file_size} bytes). "
                f"Maximum: {MAX_VIDEO_FILE_SIZE} bytes",
                status=UploadStatus.INVALID_FILE,
            )

        self.logger.debug(
            f"Video file validated: {video_path} ({file_size} bytes)",
        )

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        playlist_id: Optional[str] = None,
    ) -> UploadResult:
        """
        Upload video to YouTube.

        This implements resumable upload for reliability.
        Upload happens in chunks defined by UPLOAD_CHUNK_SIZE.

        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: Video tags (default: ["boxing", "training", "practice"])
            playlist_id: Playlist to add video to (optional)

        Returns:
            UploadResult with upload details
        """
        start_time = time.time()
        file_size = 0

        try:
            # Validate file
            self._validate_video_file(video_path)
            file_size = os.path.getsize(video_path)

            self.logger.info(
                f"Starting upload: {video_path} ({file_size} bytes)",
            )

            # Prepare video metadata
            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags or DEFAULT_VIDEO_TAGS,
                    "categoryId": YOUTUBE_CATEGORY_SPORTS,
                },
                "status": {
                    "privacyStatus": DEFAULT_PRIVACY_STATUS,
                },
            }

            # Create media upload object
            media = MediaFileUpload(
                video_path,
                chunksize=UPLOAD_CHUNK_SIZE,
                resumable=True,
            )

            # Execute upload request
            request = self.youtube_service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            # Upload with progress tracking
            video_id = self._execute_upload(request)

            # Add to playlist if specified
            target_playlist = playlist_id or self.default_playlist_id
            if target_playlist and video_id:
                self._add_to_playlist(video_id, target_playlist)

            # Calculate upload duration
            upload_duration = time.time() - start_time

            self.logger.info(
                f"✅ Upload successful: {video_id} "
                f"({upload_duration:.1f}s, {file_size} bytes)",
            )

            return UploadResult(
                success=True,
                video_id=video_id,
                status=UploadStatus.SUCCESS,
                upload_duration=upload_duration,
                file_size=file_size,
            )

        except UploaderError as e:
            # Re-raise our custom errors
            upload_duration = time.time() - start_time
            self.logger.error(f"Upload failed: {e}")
            return UploadResult(
                success=False,
                status=e.status,
                error_message=str(e),
                upload_duration=upload_duration,
                file_size=file_size,
            )

        except HttpError as e:
            # YouTube API errors
            upload_duration = time.time() - start_time
            status = self._parse_http_error(e)
            error_msg = f"YouTube API error: {e.reason}"
            self.logger.error(error_msg)

            return UploadResult(
                success=False,
                status=status,
                error_message=error_msg,
                upload_duration=upload_duration,
                file_size=file_size,
            )

        except Exception as e:
            # Unexpected errors
            upload_duration = time.time() - start_time
            error_msg = f"Unexpected upload error: {e}"
            self.logger.error(error_msg, exc_info=True)

            return UploadResult(
                success=False,
                status=UploadStatus.FAILED,
                error_message=error_msg,
                upload_duration=upload_duration,
                file_size=file_size,
            )

    def _execute_upload(self, request) -> str:
        """
        Execute resumable upload with progress tracking.

        Args:
            request: YouTube API insert request

        Returns:
            Video ID of uploaded video

        Raises:
            UploaderError: If upload fails or times out
        """
        response = None
        upload_start = time.time()
        last_progress = 0

        while response is None:
            # Check timeout
            elapsed = time.time() - upload_start
            if elapsed > UPLOAD_TIMEOUT:
                raise UploaderError(
                    f"Upload timeout after {elapsed:.1f}s",
                    status=UploadStatus.TIMEOUT,
                )

            try:
                status, response = request.next_chunk()

                if status:
                    # Log progress (only if changed significantly)
                    progress = int(status.progress() * 100)
                    if progress >= last_progress + 10:  # Log every 10%
                        self.logger.info(f"Upload progress: {progress}%")
                        last_progress = progress

            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    # Retryable server errors - wait and retry
                    self.logger.warning(
                        f"Retryable error {e.resp.status}, retrying...",
                    )
                    time.sleep(5)
                else:
                    # Non-retryable error
                    raise UploaderError(
                        f"Upload failed: {e.reason}",
                        status=self._parse_http_error(e),
                    ) from e

        # Upload complete - extract video ID
        if response and "id" in response:
            return response["id"]
        raise UploaderError(
            "Upload completed but no video ID returned",
            status=UploadStatus.FAILED,
        )

    def _add_to_playlist(self, video_id: str, playlist_id: str) -> None:
        """
        Add video to playlist.

        Args:
            video_id: YouTube video ID
            playlist_id: YouTube playlist ID

        Note: Logs warning if fails but doesn't raise - non-critical
        """
        try:
            self.youtube_service.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id,
                        },
                    },
                },
            ).execute()

            self.logger.info(f"Added video {video_id} to playlist {playlist_id}")

        except HttpError as e:
            # Don't fail upload if playlist add fails
            self.logger.warning(
                f"Failed to add video to playlist: {e.reason}",
            )

    def _parse_http_error(self, error: HttpError) -> UploadStatus:
        """
        Parse HTTP error to determine appropriate status code.

        Args:
            error: HTTP error from YouTube API

        Returns:
            Appropriate UploadStatus enum
        """
        if error.resp.status in [401, 403]:
            return UploadStatus.AUTH_ERROR
        if error.resp.status == 429:
            return UploadStatus.QUOTA_EXCEEDED
        if error.resp.status >= 500:
            return UploadStatus.NETWORK_ERROR
        return UploadStatus.FAILED

    def is_available(self) -> bool:
        """
        Check if uploader is ready.

        Returns:
            True if authenticated and service initialized
        """
        return (
            self.oauth_manager.is_authenticated() and self.youtube_service is not None
        )

    def test_connection(self) -> bool:
        """
        Test connection to YouTube API.

        Makes a simple API call to verify connectivity and auth.

        Returns:
            True if connection successful
        """
        try:
            # Simple API call - list channels
            request = self.youtube_service.channels().list(
                part="snippet",
                mine=True,
            )
            request.execute()

            self.logger.info("✅ YouTube API connection test successful")
            return True

        except Exception as e:
            self.logger.error(f"❌ YouTube API connection test failed: {e}")
            return False

    def get_upload_quota_remaining(self) -> Optional[int]:
        """
        Get remaining upload quota.

        Note: YouTube API doesn't provide direct quota info.
        This is a placeholder for future implementation.

        Returns:
            None (quota info not available via API)
        """
        # YouTube doesn't expose quota info via API
        # Would need to track usage manually or use Cloud Console
        return None
