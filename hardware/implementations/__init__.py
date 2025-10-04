"""
Hardware Implementations Package

Exposes concrete implementations of hardware interfaces.
"""

from hardware.implementations.mock_gpio import MockGPIO
from hardware.implementations.mock_tts import MockTTS
from hardware.implementations.pyttsx3_tts import PyTTSx3Engine
from hardware.implementations.rpi_gpio import RaspberryPiGPIO

# Public API
__all__ = [
    # GPIO Implementations
    "RaspberryPiGPIO",
    "MockGPIO",
    # TTS Implementations
    "PyTTSx3Engine",
    "MockTTS",
]
