"""
Mock Uploader Implementation

Simulated uploader for testing without YouTube API.
Similar to MockGPIO/MockTTS in hardware module.
"""

import logging
import os
import time
from typing import Optional
from uuid import uuid4

from upload.constants import (
    MAX_VIDEO_FILE_SIZE,
    MIN_VIDEO_FILE_SIZE,
    SUPPORTED_VIDEO_FORMATS,
    UploadStatus,
)
from upload.interfaces.uploader_interface import (
    UploaderError,
    UploaderInterface,
    UploadResult,
)


class MockUploader(UploaderInterface):
    """
    Mock video uploader for testing.

    This simulates upload timing and behavior without actually uploading.
    Useful for:
    - Unit tests
    - Development without YouTube credentials
    - CI/CD pipelines
    """

    def __init__(
        self,
        simulate_timing: bool = True,
        fail_rate: float = 0.0,
        playlist_id: Optional[str] = None,
    ):
        """
        Initialize mock uploader.

        Args:
            simulate_timing: If True, simulate realistic upload duration
            fail_rate: Probability of upload failure (0.0 to 1.0)
            playlist_id: Mock playlist ID

        Example:
            # Fast mock for unit tests
            uploader = MockUploader(simulate_timing=False)

            # Realistic mock for integration tests
            uploader = MockUploader(simulate_timing=True)

            # Test error handling
            uploader = MockUploader(fail_rate=0.5)
        """
        self.logger = logging.getLogger(__name__)
        self.simulate_timing = simulate_timing
        self.fail_rate = fail_rate
        self.playlist_id = playlist_id

        # Track upload history for testing
        self.upload_history: list[dict] = []

        self.logger.info(
            f"Mock Uploader initialized "
            f"(timing: {simulate_timing}, fail_rate: {fail_rate})",
        )

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str = "",
        tags: Optional[list[str]] = None,
        playlist_id: Optional[str] = None,
    ) -> UploadResult:
        """
        Simulate video upload.

        Validates file and simulates upload timing.
        """
        start_time = time.time()
        file_size = 0

        try:
            # Validate file (real validation)
            self._validate_video_file(video_path)
            file_size = os.path.getsize(video_path)

            self.logger.info(
                f"[MOCK] Starting upload: {video_path} ({file_size} bytes)",
            )

            # Simulate upload timing
            if self.simulate_timing:
                # Estimate: ~5 MB/s upload speed
                upload_seconds = file_size / (5 * 1024 * 1024)
                # Add base overhead
                upload_seconds += 2.0

                self.logger.debug(
                    f"[MOCK] Simulating {upload_seconds:.1f}s upload",
                )
                time.sleep(upload_seconds)

            # Simulate random failures
            import random

            if random.random() < self.fail_rate:
                raise UploaderError(
                    "Simulated upload failure",
                    status=UploadStatus.NETWORK_ERROR,
                )

            # Generate fake video ID
            video_id = f"mock_{uuid4().hex[:11]}"

            # Track upload
            upload_record = {
                "video_id": video_id,
                "video_path": video_path,
                "title": title,
                "description": description,
                "tags": tags,
                "playlist_id": playlist_id or self.playlist_id,
                "file_size": file_size,
                "timestamp": time.time(),
            }
            self.upload_history.append(upload_record)

            upload_duration = time.time() - start_time

            self.logger.info(
                f"[MOCK] ✅ Upload successful: {video_id} ({upload_duration:.1f}s)",
            )

            return UploadResult(
                success=True,
                video_id=video_id,
                status=UploadStatus.SUCCESS,
                upload_duration=upload_duration,
                file_size=file_size,
            )

        except UploaderError as e:
            upload_duration = time.time() - start_time
            self.logger.error(f"[MOCK] Upload failed: {e}")

            return UploadResult(
                success=False,
                status=e.status,
                error_message=str(e),
                upload_duration=upload_duration,
                file_size=file_size,
            )

        except Exception as e:
            upload_duration = time.time() - start_time
            error_msg = f"Mock upload error: {e}"
            self.logger.error(error_msg)

            return UploadResult(
                success=False,
                status=UploadStatus.FAILED,
                error_message=error_msg,
                upload_duration=upload_duration,
                file_size=file_size,
            )

    def _validate_video_file(self, video_path: str) -> None:
        """Validate video file (same as real uploader)"""
        if not os.path.exists(video_path):
            raise UploaderError(
                f"Video file not found: {video_path}",
                status=UploadStatus.INVALID_FILE,
            )

        file_ext = os.path.splitext(video_path)[1].lower()
        if file_ext not in SUPPORTED_VIDEO_FORMATS:
            raise UploaderError(
                f"Unsupported format: {file_ext}",
                status=UploadStatus.INVALID_FILE,
            )

        file_size = os.path.getsize(video_path)
        if file_size < MIN_VIDEO_FILE_SIZE:
            raise UploaderError(
                f"File too small: {file_size} bytes",
                status=UploadStatus.INVALID_FILE,
            )

        if file_size > MAX_VIDEO_FILE_SIZE:
            raise UploaderError(
                f"File too large: {file_size} bytes",
                status=UploadStatus.INVALID_FILE,
            )

    def is_available(self) -> bool:
        """Mock uploader is always available"""
        return True

    def test_connection(self) -> bool:
        """Simulate connection test (always succeeds unless fail_rate)"""
        import random

        if random.random() < self.fail_rate:
            self.logger.warning("[MOCK] Connection test failed (simulated)")
            return False

        self.logger.info("[MOCK] ✅ Connection test successful")
        return True

    def get_upload_quota_remaining(self) -> Optional[int]:
        """Return fake quota for testing"""
        return 10000  # Fake quota

    # =========================================================================
    # TESTING HELPER METHODS
    # =========================================================================

    def get_upload_history(self) -> list[dict]:
        """
        Get list of all uploads performed.

        Returns:
            List of upload records
        """
        return self.upload_history.copy()

    def clear_history(self) -> None:
        """Clear upload history"""
        self.upload_history.clear()
        self.logger.debug("[MOCK] Upload history cleared")

    def get_last_upload(self) -> Optional[dict]:
        """
        Get most recent upload.

        Returns:
            Last upload record, or None
        """
        return self.upload_history[-1] if self.upload_history else None

    def was_uploaded(self, video_path: str) -> bool:
        """
        Check if video was uploaded.

        Args:
            video_path: Path to check

        Returns:
            True if video in history
        """
        return any(record["video_path"] == video_path for record in self.upload_history)
