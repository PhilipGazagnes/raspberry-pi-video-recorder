"""
Audio Package

Components for audio feedback system.
"""

from hardware.audio.audio_queue import AudioQueue
from hardware.audio.message_library import MessageLibrary

# Public API
__all__ = [
    "AudioQueue",
    "MessageLibrary",
]
