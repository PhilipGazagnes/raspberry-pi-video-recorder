"""
Recording Controllers Package

High-level recording controllers that orchestrate video capture.
"""

from recording.controllers.camera_manager import CameraManager
from recording.controllers.recording_session import RecordingSession

# Public API
__all__ = [
    "CameraManager",
    "RecordingSession",
]
