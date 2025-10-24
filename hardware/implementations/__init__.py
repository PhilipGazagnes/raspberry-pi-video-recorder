"""
Hardware Implementations Package

Exposes concrete implementations of hardware interfaces.
"""

from hardware.implementations.mock_gpio import MockGPIO
from hardware.implementations.mock_tts import MockTTS
from hardware.implementations.pyttsx3_tts import PyTTSx3Engine
from hardware.implementations.rpi_gpio import RaspberryPiGPIO

# Public API (sorted alphabetically)
__all__ = [
    "MockGPIO",
    "MockTTS",
    "PyTTSx3Engine",
    "RaspberryPiGPIO",
]
