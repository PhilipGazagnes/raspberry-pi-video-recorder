"""
Recording Module

Video capture and recording session management for Raspberry Pi.

Provides automatic detection and graceful fallback between real FFmpeg
capture and mock implementations for testing.

Public API:
    - RecordingFactory: Factory for creating capture implementations
    - create_capture: Quick capture creation with auto-detection
    - CameraManager: High-level camera lifecycle management
    - RecordingSession: Session management with timing and callbacks
    - VideoCaptureInterface: Capture contract
    - CaptureError: Custom exceptions
    - RecordingState: State enumeration

Usage:
    from recording import CameraManager, RecordingSession

    # Auto-detects FFmpeg vs mock
    camera = CameraManager()
    session = RecordingSession(camera)

    # Start recording with callbacks
    session.on_warning = lambda: print("1 min left!")
    session.start(output_file="video.mp4", duration=600)
"""

from recording.constants import RecordingState
from recording.controllers.camera_manager import CameraManager
from recording.controllers.recording_session import RecordingSession
from recording.factory import RecordingFactory, create_capture
from recording.interfaces.video_capture_interface import (
    CaptureError,
    VideoCaptureInterface,
)
from recording.utils.recording_utils import generate_filename

__all__ = [
    "CameraManager",
    "CaptureError",
    "RecordingFactory",
    "RecordingSession",
    "RecordingState",
    "VideoCaptureInterface",
    "create_capture",
    "generate_filename",
]
