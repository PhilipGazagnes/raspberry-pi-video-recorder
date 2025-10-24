"""
Controllers Package

High-level hardware controllers for the video recording system.
"""

from hardware.controllers.audio_controller import AudioController
from hardware.controllers.button_controller import ButtonController, ButtonPress
from hardware.controllers.led_controller import LEDController

# Public API (sorted alphabetically)
__all__ = [
    "AudioController",
    "ButtonController",
    "ButtonPress",
    "LEDController",
]
