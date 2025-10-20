"""
Upload Module

Video upload system for YouTube with OAuth authentication.

Public API:
    - UploadController: High-level upload coordinator
    - UploadResult: Upload operation result
    - UploadStatus: Status codes
    - create_uploader: Factory function

Usage:
    from upload import UploadController

    controller = UploadController()
    result = controller.upload_video(
        video_path="/path/to/video.mp4",
        timestamp="2025-10-12 18:30:45"
    )
"""

from upload.constants import UploadStatus
from upload.controllers.upload_controller import UploadController
from upload.factory import create_uploader
from upload.interfaces.uploader_interface import UploadResult, UploaderError

# Public API
__all__ = [
    "UploadController",
    "UploadResult",
    "UploadStatus",
    "UploaderError",
    "create_uploader",
]
