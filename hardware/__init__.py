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
    - AudioController: High-level audio/TTS controller
    - LEDController: LED status display controller
    - ButtonController: Button input controller

Usage:
    from hardware import create_gpio, create_tts

    # Auto-detects real vs mock hardware
    gpio = create_gpio()
    tts = create_tts()

    # Or use high-level controllers
    from hardware import AudioController, LEDController, ButtonController

    audio = AudioController()
    led = LEDController()
    button = ButtonController()
"""

from hardware.controllers.audio_controller import AudioController
from hardware.controllers.button_controller import ButtonController
from hardware.controllers.led_controller import LEDController
from hardware.factory import HardwareFactory, create_gpio, create_tts
from hardware.interfaces.gpio_interface import GPIOInterface
from hardware.interfaces.tts_interface import TTSInterface

__all__ = [
    "AudioController",
    "ButtonController",
    "GPIOInterface",
    "HardwareFactory",
    "LEDController",
    "TTSInterface",
    "create_gpio",
    "create_tts",
]
