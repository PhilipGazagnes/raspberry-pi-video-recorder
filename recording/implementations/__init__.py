"""
Recording Implementations Package

Exposes concrete implementations of recording interfaces.
"""

from recording.implementations.ffmpeg_capture import FFmpegCapture
from recording.implementations.mock_capture import MockCapture

# Public API
__all__ = [
    "FFmpegCapture",
    "MockCapture",
]
