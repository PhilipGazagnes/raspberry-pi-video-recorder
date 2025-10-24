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

# Public API (sorted alphabetically)
__all__ = [
    "EdgeDetection",
    "GPIOError",
    "GPIOInterface",
    "PinMode",
    "PinState",
    "PullMode",
    "TTSError",
    "TTSInterface",
]
