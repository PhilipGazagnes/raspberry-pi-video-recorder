"""
Hardware Module

GPIO and TTS hardware abstraction for Raspberry Pi.

Provides automatic detection and graceful fallback between real hardware
and mock implementations for testing.

Public API:
    - HardwareFactory: Factory for creating hardware components
    - create_gpio: Quick GPIO creation with auto-detection
    - create_tts: Quick TTS creation with auto-detection
    - GPIOInterface: GPIO contract
    - TTSInterface: TTS contract

Usage:
    from hardware import create_gpio, create_tts

    # Auto-detects real vs mock hardware
    gpio = create_gpio()
    tts = create_tts()

    # Force mock for testing
    gpio = create_gpio(force_mock=True)
"""

from hardware.factory import HardwareFactory, create_gpio, create_tts
from hardware.interfaces.gpio_interface import GPIOInterface
from hardware.interfaces.tts_interface import TTSInterface

__all__ = [
    "GPIOInterface",
    "HardwareFactory",
    "TTSInterface",
    "create_gpio",
    "create_tts",
]
