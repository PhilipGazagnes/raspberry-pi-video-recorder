"""
Hardware Constants

This file centralizes all magic numbers, timing values, and configuration strings
used throughout the hardware module. This follows the DRY (Don't Repeat Yourself)
principle and makes it easy to adjust hardware behavior in one place.

Why separate constants?
- Easy to tune timing without hunting through code
- Clear documentation of hardware behavior
- Type safety and IDE autocomplete
- Easy to test with different values
"""

from enum import Enum

from config.settings import (
    GPIO_BUTTON_PIN,
    GPIO_LED_GREEN,
    GPIO_LED_ORANGE,
    GPIO_LED_RED,
)

# =============================================================================
# GPIO PIN CONFIGURATION
# =============================================================================
# Import from central config.settings to maintain single source of truth
# NEVER modify here - change in config/settings.py instead!


# =============================================================================
# BUTTON TIMING CONSTANTS
# =============================================================================
# Button debouncing prevents false triggers from electrical noise
# when the button is pressed/released

# How long to ignore button signals after a press (in seconds)
# 50ms is standard for mechanical buttons - electrical bounce settles by then
BUTTON_DEBOUNCE_TIME = 0.05

# Maximum time between two presses to count as "double tap" (in seconds)
# 500ms feels natural - longer feels sluggish, shorter is hard to trigger
BUTTON_DOUBLE_TAP_WINDOW = 0.5


# =============================================================================
# LED TIMING CONSTANTS
# =============================================================================
# LED blink rates for different states

# Normal recording blink rate (in seconds)
# 0.5s = 1Hz (on/off per second) - clearly visible but not annoying
LED_BLINK_INTERVAL_NORMAL = 0.5

# Fast error flash rate (in seconds)
# 0.1s = 5Hz - rapid flashing grabs attention for errors
LED_BLINK_INTERVAL_FAST = 0.1

# How long to flash error LED (in seconds)
LED_ERROR_FLASH_DURATION = 2.0


# =============================================================================
# AUDIO CONFIGURATION
# =============================================================================
# Text-to-speech settings

# Speaking rate in words per minute
# 125 WPM is clear and not rushed (typical speech is 150-160 WPM)
TTS_SPEECH_RATE = 125

# Volume level (0.0 to 1.0)
# 0.8 is loud enough to hear but not distorted
TTS_VOLUME = 0.8

# Preferred voice ID pattern (for French voice selection)
# This matches the pyttsx3 voice ID pattern for French voices
TTS_FRENCH_VOICE_PATTERN = "roa/fr"


# =============================================================================
# AUDIO MESSAGE LIBRARY
# =============================================================================
# All voice messages used in the system
# Centralized here so you can easily translate or modify all messages


class AudioMessage(Enum):
    """
    Enum for audio messages - this prevents typos and provides IDE autocomplete.

    Why use Enum instead of plain strings?
    - Type safety: AudioMessage.SYSTEM_READY vs "system_ready" (typo-proof)
    - Autocomplete: IDE suggests all available messages
    - Refactoring: Change the value without breaking code
    """

    # System status messages
    SYSTEM_READY = "system_ready"
    SYSTEM_ERROR = "system_error"
    SYSTEM_SHUTDOWN = "system_shutdown"

    # Recording lifecycle messages
    RECORDING_START = "recording_start"
    RECORDING_STOP = "recording_stop"
    RECORDING_EXTENDED = "recording_extended"

    # Warning messages
    ONE_MINUTE_WARNING = "one_minute_warning"
    EXTENSION_AVAILABLE = "extension_available"

    # Status messages
    READY_FOR_NEXT = "ready_for_next"
    UPLOAD_COMPLETE = "upload_complete"
    UPLOAD_FAILED = "upload_failed"

    # Error messages
    MEMORY_FULL = "memory_full"
    NETWORK_DISCONNECTED = "network_disconnected"
    CAMERA_ERROR = "camera_error"
    STORAGE_ERROR = "storage_error"
    UPLOAD_ERROR = "upload_error"

    # Recovery messages
    ERROR_RECOVERED = "error_recovered"
    NETWORK_RESTORED = "network_restored"


# The actual text for each message
# This is separate from the Enum so you can easily translate or customize
AUDIO_MESSAGE_TEXTS = {
    AudioMessage.SYSTEM_READY: "System ready",
    AudioMessage.SYSTEM_ERROR: "System error",
    AudioMessage.SYSTEM_SHUTDOWN: "System shutting down",
    AudioMessage.RECORDING_START: "Recording started",
    AudioMessage.RECORDING_STOP: "Recording complete, uploading",
    AudioMessage.RECORDING_EXTENDED: "5 minutes added, recording continues",
    AudioMessage.ONE_MINUTE_WARNING: "One minute remaining, press button twice to extend",
    AudioMessage.EXTENSION_AVAILABLE: "Press button twice to extend recording",
    AudioMessage.READY_FOR_NEXT: "Ready for next recording",
    AudioMessage.UPLOAD_COMPLETE: "Upload successful",
    AudioMessage.UPLOAD_FAILED: "Upload failed, will retry",
    AudioMessage.MEMORY_FULL: "Memory full",
    AudioMessage.NETWORK_DISCONNECTED: "Network disconnected",
    AudioMessage.CAMERA_ERROR: "Camera error",
    AudioMessage.STORAGE_ERROR: "Storage error",
    AudioMessage.UPLOAD_ERROR: "Upload error",
    AudioMessage.ERROR_RECOVERED: "Error resolved, system ready",
    AudioMessage.NETWORK_RESTORED: "Network connection restored",
}


# =============================================================================
# LED STATUS PATTERNS
# =============================================================================
# Defines which LEDs should be on/off for each system state


class LEDColor(Enum):
    """Individual LED colors available"""

    GREEN = "green"
    ORANGE = "orange"
    RED = "red"


class LEDPattern(Enum):
    """
    System states mapped to LED patterns.
    Each pattern defines: (green, orange, red, should_blink, blink_color)
    """

    # All off during boot
    OFF = "off"

    # Green solid when ready
    READY = "ready"

    # Green blinking during recording
    RECORDING = "recording"

    # Orange solid while processing/uploading
    PROCESSING = "processing"

    # Red solid for errors
    ERROR = "error"


# Map each pattern to its LED states
# Format: (green_on, orange_on, red_on, should_blink, blink_color)
LED_PATTERN_CONFIG = {
    LEDPattern.OFF: (False, False, False, False, None),
    LEDPattern.READY: (True, False, False, False, None),
    LEDPattern.RECORDING: (False, False, False, True, LEDColor.GREEN),
    LEDPattern.PROCESSING: (False, True, False, False, None),
    LEDPattern.ERROR: (False, False, True, False, None),
}


# =============================================================================
# THREADING CONFIGURATION
# =============================================================================
# Thread behavior settings

# How long to wait for threads to stop gracefully before forcing (seconds)
THREAD_SHUTDOWN_TIMEOUT = 2.0

# Main loop update frequency (seconds)
# 10Hz provides responsive button handling without wasting CPU
MAIN_LOOP_INTERVAL = 0.1


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
# Log level names for hardware components

LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"
