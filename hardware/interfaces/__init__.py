"""
Hardware Interfaces Package

Exposes abstract interfaces that define contracts for hardware components.
"""

from hardware.interfaces.gpio_interface import (
    EdgeDetection,
    GPIOError,
    GPIOInterface,
    PinMode,
    PinState,
    PullMode,
)
from hardware.interfaces.tts_interface import TTSError, TTSInterface

# Public API - these are the names that can be imported
__all__ = [
    # GPIO Interface
    "GPIOInterface",
    "PinMode",
    "PinState",
    "PullMode",
    "EdgeDetection",
    "GPIOError",
    # TTS Interface
    "TTSInterface",
    "TTSError",
]
