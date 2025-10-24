"""
Text-to-Speech Interface

Abstract interface for TTS engines. Allows swapping between real TTS (pyttsx3),
mock TTS (for testing), or even different TTS libraries without changing
controller code.

This demonstrates the "D" in SOLID - Dependency Inversion Principle.
High-level code (AudioController) depends on this abstraction, not on pyttsx3 directly.
"""

from abc import ABC, abstractmethod
from typing import List, Optional


class TTSInterface(ABC):
    """
    Abstract base class for Text-to-Speech engines.

    Any TTS implementation must provide these methods to work with AudioController.
    """

    @abstractmethod
    def speak(self, text: str) -> None:
        """
        Convert text to speech and play it.

        This should be a BLOCKING call - it doesn't return until speech finishes.
        The AudioController will handle making it non-blocking via queue.

        Args:
            text: Text to speak

        Raises:
            TTSError: If speech synthesis fails
        """

    @abstractmethod
    def set_rate(self, rate: int) -> None:
        """
        Set speech rate in words per minute.

        Args:
            rate: Words per minute (typical range: 100-300)

        Raises:
            TTSError: If rate is invalid or cannot be set
        """

    @abstractmethod
    def set_volume(self, volume: float) -> None:
        """
        Set speech volume.

        Args:
            volume: Volume level from 0.0 (silent) to 1.0 (maximum)

        Raises:
            TTSError: If volume is invalid or cannot be set
        """

    @abstractmethod
    def set_voice(self, voice_id: Optional[str] = None) -> None:
        """
        Set the voice to use for speech.

        Args:
            voice_id: Voice identifier (engine-specific), or None for default

        Raises:
            TTSError: If voice is not found
        """

    @abstractmethod
    def get_available_voices(self) -> List[str]:
        """
        Get list of available voice identifiers.

        Returns:
            List of voice IDs that can be passed to set_voice()
        """

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if TTS is actually available on this system.

        Returns:
            True if TTS hardware/software is working, False otherwise
        """

    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up TTS resources.
        Called when shutting down.
        """


class TTSError(Exception):
    """
    Exception raised for TTS-related errors.

    Examples:
    - TTS library not installed
    - Audio device not available
    - Invalid voice/rate/volume parameters
    """
