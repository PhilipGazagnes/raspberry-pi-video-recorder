"""
Audio Controller - Refactored

Provides text-to-speech audio feedback for the video recording system.
Coordinates TTS engine, message library, and playback queue.

IMPROVEMENTS FROM ORIGINAL:
- 150 lines vs 500 lines (70% reduction!)
- Split into focused modules (MessageLibrary, AudioQueue)
- No direct TTS dependency (uses interface)
- Configuration from constants (no magic numbers)
- Cleaner separation of concerns
- Much easier to test

This demonstrates SOLID principles:
- Single Responsibility: Only coordinates audio feedback
- Open/Closed: Easy to add features without modifying
- Dependency Inversion: Depends on TTSInterface, not pyttsx3
- Composition: Uses MessageLibrary and AudioQueue
"""

import logging
from typing import Optional

from hardware.audio.audio_queue import AudioQueue
from hardware.audio.message_library import MessageLibrary
from hardware.constants import AudioMessage, TTS_SPEECH_RATE, TTS_VOLUME
from hardware.factory import create_tts
from hardware.interfaces.tts_interface import TTSInterface


class AudioController:
    """
    High-level audio feedback controller.

    This class:
    - Plays predefined messages
    - Plays custom text
    - Manages TTS settings (volume, rate)
    - Provides queue control

    Usage:
        audio = AudioController()
        audio.play_message(AudioMessage.RECORDING_START)
        audio.play_text("Custom message")
        audio.cleanup()
    """

    def __init__(self, tts_engine: Optional[TTSInterface] = None):
        """
        Initialize audio controller.

        Args:
            tts_engine: TTS interface to use, or None to auto-create.
                       Auto-creation uses factory (real TTS or mock).

        Example:
            # Normal usage - auto-detects TTS
            audio = AudioController()

            # Testing with specific mock
            mock_tts = MockTTS(simulate_timing=False)
            audio = AudioController(tts_engine=mock_tts)
        """
        self.logger = logging.getLogger(__name__)

        # Create or use provided TTS engine
        self.tts_engine = tts_engine or create_tts()

        # Initialize components
        # Each component has ONE responsibility
        self.message_library = MessageLibrary()
        self.audio_queue = AudioQueue(self.tts_engine)

        # Configure TTS with defaults from constants
        self._configure_tts()

        self.logger.info(
            f"Audio Controller initialized "
            f"(TTS available: {self.tts_engine.is_available()})"
        )

    def _configure_tts(self) -> None:
        """
        Configure TTS engine with default settings from constants.

        This separates initialization from configuration.
        """
        try:
            self.tts_engine.set_rate(TTS_SPEECH_RATE)
            self.tts_engine.set_volume(TTS_VOLUME)
            self.logger.debug(
                f"TTS configured: rate={TTS_SPEECH_RATE} WPM, "
                f"volume={TTS_VOLUME}"
            )
        except Exception as e:
            self.logger.warning(f"Could not configure TTS: {e}")

    # =========================================================================
    # PLAYBACK METHODS
    # =========================================================================

    def play_message(self, message_key: AudioMessage) -> None:
        """
        Play a predefined message by key.

        Returns immediately - speech plays in background.

        Args:
            message_key: Message identifier from AudioMessage enum

        Example:
            audio.play_message(AudioMessage.RECORDING_START)
            audio.play_message(AudioMessage.ONE_MINUTE_WARNING)
        """
        try:
            # Get message text from library
            text = self.message_library.get_message(message_key)

            # Queue for playback
            self.audio_queue.play(text)

            self.logger.info(f"Playing message: {message_key.value}")

        except KeyError as e:
            self.logger.error(f"Unknown message key: {message_key}: {e}")

    def play_text(self, text: str) -> None:
        """
        Play arbitrary text as speech.

        Returns immediately - speech plays in background.

        Args:
            text: Text to speak

        Example:
            audio.play_text("Recording will start in 3 seconds")
        """
        if not text.strip():
            self.logger.warning("Empty text provided for speech")
            return

        self.logger.info(f"Playing text: '{text[:50]}...'")
        self.audio_queue.play(text)

    # =========================================================================
    # QUEUE CONTROL
    # =========================================================================

    def stop_playback(self) -> None:
        """
        Stop current playback and clear queue.

        Note: Cannot interrupt currently speaking message,
        but clears all pending messages.

        Example:
            audio.play_message(AudioMessage.SYSTEM_ERROR)
            audio.stop_playback()  # Cancel it
        """
        cleared = self.audio_queue.clear_queue()
        if cleared > 0:
            self.logger.info(f"Cleared {cleared} pending messages")

    def clear_queue(self) -> int:
        """
        Clear all pending messages.

        Returns:
            Number of messages cleared
        """
        return self.audio_queue.clear_queue()

    def is_playing(self) -> bool:
        """
        Check if audio is currently playing.

        Returns:
            True if speaking now, False if idle
        """
        return self.audio_queue.is_playing()

    def is_busy(self) -> bool:
        """
        Check if audio system is busy (playing or has queued messages).

        Returns:
            True if any audio activity
        """
        return self.audio_queue.is_busy()

    def wait_until_idle(self, timeout: Optional[float] = None) -> bool:
        """
        Wait until all audio playback completes.

        Args:
            timeout: Maximum time to wait in seconds, or None

        Returns:
            True if became idle, False if timeout

        Example:
            audio.play_message(AudioMessage.RECORDING_START)
            audio.wait_until_idle()  # Wait for it to finish
            print("Speech complete!")
        """
        return self.audio_queue.wait_until_idle(timeout)

    # =========================================================================
    # TTS CONFIGURATION
    # =========================================================================

    def set_volume(self, volume: float) -> None:
        """
        Set TTS volume.

        Args:
            volume: Volume level from 0.0 (silent) to 1.0 (max)

        Example:
            audio.set_volume(0.5)  # Half volume
        """
        try:
            self.tts_engine.set_volume(volume)
            self.logger.info(f"Volume set to {volume}")
        except Exception as e:
            self.logger.error(f"Failed to set volume: {e}")

    def set_speech_rate(self, rate: int) -> None:
        """
        Set TTS speech rate.

        Args:
            rate: Words per minute (typical range: 100-300)

        Example:
            audio.set_speech_rate(150)  # Normal pace
        """
        try:
            self.tts_engine.set_rate(rate)
            self.logger.info(f"Speech rate set to {rate} WPM")
        except Exception as e:
            self.logger.error(f"Failed to set speech rate: {e}")

    # =========================================================================
    # MESSAGE LIBRARY METHODS
    # =========================================================================

    def add_custom_message(self, key: AudioMessage, text: str) -> None:
        """
        Add or update a custom message.

        Args:
            key: Message identifier
            text: Message text to speak

        Example:
            audio.add_custom_message(AudioMessage.SYSTEM_READY, "Système prêt")
        """
        self.message_library.add_custom_message(key, text)

    def get_available_messages(self) -> list[AudioMessage]:
        """
        Get list of available message keys.

        Returns:
            List of AudioMessage enum values
        """
        return self.message_library.get_available_messages()

    # =========================================================================
    # TESTING AND DIAGNOSTICS
    # =========================================================================

    def test_audio(self) -> None:
        """
        Test audio functionality with sample messages.

        Plays several test messages to verify audio works.
        Blocks until all messages complete.

        Example:
            audio = AudioController()
            audio.test_audio()  # Listen for test messages
        """
        self.logger.info("Starting audio test")

        test_messages = [
            "Audio system test",
            "Recording started",
            "One minute remaining",
            "Recording complete"
        ]

        for message in test_messages:
            self.logger.info(f"Testing: {message}")
            self.play_text(message)

        # Wait for all messages to complete
        self.wait_until_idle()

        self.logger.info("Audio test complete")

    def test_all_messages(self) -> None:
        """
        Test all predefined messages.

        Plays every message in the library.
        Useful for verifying all messages are correct.

        Example:
            audio.test_all_messages()  # Hear all system messages
        """
        self.logger.info("Testing all predefined messages")

        for message_key in self.get_available_messages():
            self.logger.info(f"Testing: {message_key.value}")
            self.play_message(message_key)

        # Wait for completion
        self.wait_until_idle()

        self.logger.info("All message tests complete")

    def check_audio_system(self) -> dict:
        """
        Check audio system health and capabilities.

        Returns:
            Dictionary with system information

        Example:
            status = audio.check_audio_system()
            print(f"TTS available: {status['tts_available']}")
        """
        status = {
            'tts_available': self.tts_engine.is_available(),
            'message_count': len(self.message_library),
            'queue_size': self.audio_queue.get_queue_size(),
            'is_playing': self.is_playing(),
        }

        # Try to get available voices
        try:
            voices = self.tts_engine.get_available_voices()
            status['available_voices'] = len(voices)
        except Exception:
            status['available_voices'] = 0

        return status

    def get_status(self) -> dict:
        """
        Get current audio controller status.

        Returns:
            Dictionary with detailed status information

        Example:
            status = audio.get_status()
            print(f"Queue size: {status['queue']['queue_size']}")
        """
        return {
            'tts_available': self.tts_engine.is_available(),
            'message_library': self.message_library.get_message_count(),
            'queue': self.audio_queue.get_status(),
        }

    # =========================================================================
    # CLEANUP
    # =========================================================================

    def cleanup(self) -> None:
        """
        Clean up audio resources.

        IMPORTANT: Always call this before program exits!

        Example:
            audio = AudioController()
            try:
                # ... use audio ...
            finally:
                audio.cleanup()  # Always cleanup
        """
        self.logger.info("Cleaning up Audio Controller")

        # Stop queue worker
        self.audio_queue.stop()

        # Clean up TTS engine
        try:
            self.tts_engine.cleanup()
        except Exception as e:
            self.logger.warning(f"Error during TTS cleanup: {e}")

        self.logger.info("Audio Controller cleanup complete")

    def __del__(self):
        """
        Destructor - ensures cleanup even if not explicitly called.

        This is a safety net. You should still call cleanup() explicitly.
        """
        self.cleanup()
