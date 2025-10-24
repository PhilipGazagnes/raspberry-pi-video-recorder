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
    "CameraBusyError",
    "CameraNotFoundError",
    # Exceptions
    "CaptureError",
    "CaptureProcessError",
    "StorageFullError",
    # Interface
    "VideoCaptureInterface",
]
