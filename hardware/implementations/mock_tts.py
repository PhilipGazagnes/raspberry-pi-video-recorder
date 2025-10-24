"""
Mock TTS Implementation

Simulated Text-to-Speech for development and testing.
Logs messages instead of actually speaking them.

Perfect for:
- Unit tests that don't need real audio
- CI/CD pipelines
- Silent development mode
- Audio system debugging
"""

import logging
import time
from typing import Any, Dict, List, Optional

from hardware.interfaces.tts_interface import TTSError, TTSInterface


class MockTTS(TTSInterface):
    """
    Mock Text-to-Speech engine that logs instead of speaking.

    This simulates TTS timing (speech takes time) but doesn't produce audio.
    Useful for testing audio queue logic without actual speech.
    """

    def __init__(self, simulate_timing: bool = True):
        """
        Initialize mock TTS.

        Args:
            simulate_timing: If True, speak() delays to simulate real speech duration.
                           If False, speak() returns immediately (faster tests).
        """
        self.logger = logging.getLogger(__name__)
        self.simulate_timing = simulate_timing

        # Configuration that matches real TTS
        self._config = {
            "rate": 125,  # Words per minute
            "volume": 0.8,
            "voice_id": "mock_voice",
        }

        # Track what was spoken (useful for testing)
        self.speech_history: list[str] = []

        self.logger.info(
            f"Mock TTS initialized (simulate_timing: {simulate_timing})",
        )

    def speak(self, text: str) -> None:
        """
        "Speak" text by logging it.

        If simulate_timing is True, delays to mimic real speech duration.
        This tests queue behavior without actual audio.
        """
        if not text.strip():
            self.logger.warning("[MOCK TTS] Empty text provided")
            return

        # Log the speech
        self.logger.info(f"[MOCK TTS] Speaking: '{text}'")

        # Track history for tests to verify
        self.speech_history.append(text)

        if self.simulate_timing:
            # Simulate speech duration based on text length and rate
            # Rough estimate: 1 word = ~0.5 seconds at 125 WPM
            word_count = len(text.split())
            duration = word_count * (60.0 / self._config["rate"])

            # Add base overhead (engine startup, etc.)
            duration += 0.2

            self.logger.debug(
                f"[MOCK TTS] Simulating {duration:.2f}s speech for {word_count} words",
            )
            time.sleep(duration)

    def set_rate(self, rate: int) -> None:
        """Set speech rate (affects simulated timing)"""
        if not (50 <= rate <= 400):
            raise TTSError(f"Invalid rate: {rate}. Expected 50-400 WPM")

        self._config["rate"] = rate
        self.logger.info(f"[MOCK TTS] Rate set to {rate} WPM")

    def set_volume(self, volume: float) -> None:
        """Set volume (logged but doesn't affect mock)"""
        if not (0.0 <= volume <= 1.0):
            raise TTSError(f"Invalid volume: {volume}. Expected 0.0-1.0")

        self._config["volume"] = volume
        self.logger.info(f"[MOCK TTS] Volume set to {volume}")

    def set_voice(self, voice_id: Optional[str] = None) -> None:
        """Set voice (logged but doesn't affect mock)"""
        self._config["voice_id"] = voice_id or "mock_voice"
        self.logger.info(f"[MOCK TTS] Voice set to {self._config['voice_id']}")

    def get_available_voices(self) -> List[str]:
        """Return fake voice list for testing"""
        return [
            "mock_voice",
            "mock_voice_french",
            "mock_voice_english",
        ]

    def is_available(self) -> bool:
        """Mock TTS is always available"""
        return True

    def cleanup(self) -> None:
        """Clean up (nothing to do for mock)"""
        self.logger.debug("[MOCK TTS] Cleanup called")

    # =========================================================================
    # TESTING HELPER METHODS (not part of TTSInterface)
    # =========================================================================

    def get_speech_history(self) -> List[str]:
        """
        Get list of all text that was spoken.
        Useful for tests to verify correct messages were played.

        Returns:
            List of text strings in the order they were spoken
        """
        return self.speech_history.copy()

    def clear_history(self) -> None:
        """Clear speech history (useful between test cases)"""
        self.speech_history.clear()
        self.logger.debug("[MOCK TTS] History cleared")

    def get_last_speech(self) -> Optional[str]:
        """
        Get the most recently spoken text.

        Returns:
            Last spoken text, or None if nothing was spoken yet
        """
        return self.speech_history[-1] if self.speech_history else None

    def was_spoken(self, text: str) -> bool:
        """
        Check if specific text was spoken.

        Args:
            text: Text to search for

        Returns:
            True if text appears in speech history
        """
        return text in self.speech_history

    def get_config(self) -> Dict[str, Any]:
        """
        Get current TTS configuration (for test verification).

        Returns:
            Dictionary with rate, volume, voice_id
        """
        return self._config.copy()
