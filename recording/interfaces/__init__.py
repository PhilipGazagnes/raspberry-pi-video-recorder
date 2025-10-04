"""
Recording Interfaces Package

Exposes abstract interfaces for recording components.
"""

from recording.interfaces.video_capture_interface import (
    CameraBusyError,
    CameraNotFoundError,
    CaptureError,
    CaptureProcessError,
    StorageFullError,
    VideoCaptureInterface,
)

# Public API
__all__ = [
    # Interface
    "VideoCaptureInterface",
    # Exceptions
    "CaptureError",
    "CameraNotFoundError",
    "CameraBusyError",
    "StorageFullError",
    "CaptureProcessError",
]
