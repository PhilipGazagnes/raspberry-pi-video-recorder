"""
pyttsx3 TTS Implementation

Concrete implementation of TTSInterface using the pyttsx3 library.
pyttsx3 is offline TTS that works on Windows, Mac, and Linux.

Why wrap pyttsx3?
1. Your AudioController doesn't depend directly on pyttsx3
2. Easy to swap for other TTS (Google Cloud TTS, Amazon Polly, etc.)
3. Easier testing with MockTTS
4. Clean error handling
"""

import logging
import time
from typing import List, Optional

try:
    import pyttsx3

    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

from hardware.interfaces.tts_interface import TTSError, TTSInterface


class PyTTSx3Engine(TTSInterface):
    """
    Text-to-Speech implementation using pyttsx3 library.

    pyttsx3 issues:
    - Engine instances can have thread safety issues
    - Keeping engines around can cause audio cutoff
    - Best practice: Create fresh engine for each speech

    This wrapper handles these quirks so AudioController doesn't have to.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        if not TTS_AVAILABLE:
            raise TTSError(
                "pyttsx3 not available. Install with: pip install pyttsx3",
            )

        # Store configuration instead of keeping an engine instance
        # This prevents thread safety issues and audio cutoff
        self._config = {
            "rate": 125,
            "volume": 0.8,
            "voice_id": None,
        }

        # Initialize voice configuration
        self._initialize_voice_config()

        self.logger.info("pyttsx3 TTS engine configured")

    def _initialize_voice_config(self) -> None:
        """
        Initialize voice configuration by querying available voices.

        This creates a temporary engine just to get voice information,
        then disposes of it. This is safer than keeping a persistent engine.
        """
        try:
            temp_engine = pyttsx3.init()
            voices = temp_engine.getProperty("voices")

            if voices:
                # Try to find a French voice (for your project)
                for voice in voices:
                    if "roa/fr" in voice.id or "french" in voice.name.lower():
                        self._config["voice_id"] = voice.id
                        self.logger.info(f"Found French voice: {voice.name}")
                        break
                else:
                    # No French voice found, use first available
                    self._config["voice_id"] = voices[0].id
                    self.logger.info(f"Using default voice: {voices[0].name}")

            # Clean up temporary engine
            del temp_engine

        except Exception as e:
            self.logger.warning(f"Could not initialize voice config: {e}")
            # Continue anyway - speak() will try again

    def _create_engine(self) -> pyttsx3.Engine:
        """
        Create a fresh TTS engine with current configuration.

        Why create a new engine each time?
        - Prevents audio cutoff issues
        - Avoids thread safety problems
        - Ensures clean state for each speech

        Trade-off: Slightly slower, but much more reliable.
        """
        try:
            engine = pyttsx3.init()

            # Apply configuration
            if self._config["voice_id"]:
                engine.setProperty("voice", self._config["voice_id"])
            engine.setProperty("rate", self._config["rate"])
            engine.setProperty("volume", self._config["volume"])

            # DELAY 0: 0.1 seconds after engine creation
            # WHY 0.1s (100ms): Allows underlying TTS engine to fully
            #   initialize
            # Context: Platform TTS engines (espeak/SAPI/nsss) need time to
            #   load voice data and initialize audio drivers after
            #   setProperty() calls
            # Tradeoff: 100ms delay is imperceptible but prevents
            #   initialization race conditions
            # Risk: Without this, engine.say() might be called before audio
            #   subsystem is ready, causing either silence or crashes on some
            #   platforms (especially Raspberry Pi)
            # Source: This is a documented quirk in pyttsx3 - engine is
            #   "ready" but not *actually* ready
            time.sleep(0.1)

            return engine

        except Exception as e:
            raise TTSError(f"Failed to create TTS engine: {e}") from e

    def speak(self, text: str) -> None:
        """
        Convert text to speech and play it.

        This is BLOCKING - doesn't return until speech finishes.
        AudioController handles making it non-blocking via queue.
        """
        if not text.strip():
            self.logger.warning("Empty text provided for speech")
            return

        engine = None
        try:
            # Create fresh engine for this speech
            engine = self._create_engine()

            # Queue the text
            engine.say(text)

            # WHY these specific delay values: Work around pyttsx3 audio timing
            #   quirks
            # Context: pyttsx3 has known issues with audio cutoff and timing
            #   across platforms. These delays are empirically determined
            #   workarounds for library bugs
            # Background: pyttsx3 wraps platform TTS engines (espeak/SAPI/nsss)
            #   which have different timing behaviors. The library doesn't
            #   always wait for audio buffers to fully initialize or drain.

            # DELAY 1: 0.05 seconds BEFORE runAndWait()
            # WHY 0.05s (50ms): Allows audio subsystem to initialize before
            #   playback starts
            # Context: Without this, first syllable sometimes gets clipped on
            #   Linux (espeak)
            # Tradeoff: 50ms is imperceptible to users but prevents audio
            #   cutoff
            # Source: Common workaround in pyttsx3 GitHub issues #78, #118,
            #   #234
            # Risk: Too short (< 20ms) = still get cutoff; Too long (> 200ms)
            #   = noticeable pause
            time.sleep(0.05)

            # This blocks until speech completes
            engine.runAndWait()

            # DELAY 2: 0.1 seconds AFTER runAndWait()
            # WHY 0.1s (100ms): Ensures audio buffer fully drains before
            #   engine cleanup
            # Context: runAndWait() sometimes returns slightly before audio
            #   finishes playing. Deleting engine too quickly can truncate
            #   final syllables
            # Tradeoff: Small delay ensures clean audio completion
            # Source: Recommended in pyttsx3 docs and multiple GitHub issues
            # Risk: Without this delay, last word can be cut off when engine
            #   is deleted
            # Alternative: Could use engine.endLoop() but it's not reliable
            #   across platforms
            time.sleep(0.1)

            self.logger.debug(f"Spoke: '{text[:30]}...'")

        except Exception as e:
            raise TTSError(f"Speech failed: {e}") from e

        finally:
            # Always clean up the engine
            if engine:
                try:
                    engine.stop()
                except Exception:
                    pass  # Ignore errors during cleanup
                del engine

    def set_rate(self, rate: int) -> None:
        """
        Set speech rate in words per minute.

        Typical range: 100-300 WPM
        - 100 WPM: Very slow (for accessibility)
        - 150 WPM: Normal conversational pace
        - 200 WPM: Fast but understandable
        - 300 WPM: Very fast (podcast on 2x speed)
        """
        if not (50 <= rate <= 400):
            raise TTSError(
                f"Invalid speech rate: {rate}. Expected range: 50-400 WPM",
            )

        self._config["rate"] = rate
        self.logger.info(f"Speech rate set to {rate} WPM")

    def set_volume(self, volume: float) -> None:
        """
        Set speech volume (0.0 to 1.0).

        0.0 = Silent (useful for testing)
        0.5 = Half volume
        1.0 = Maximum volume
        """
        if not (0.0 <= volume <= 1.0):
            raise TTSError(
                f"Invalid volume: {volume}. Expected range: 0.0-1.0",
            )

        self._config["volume"] = volume
        self.logger.info(f"Volume set to {volume}")

    def set_voice(self, voice_id: Optional[str] = None) -> None:
        """
        Set the voice to use.

        Args:
            voice_id: Voice identifier from get_available_voices(),
                     or None to use default
        """
        if voice_id is not None:
            # Validate voice exists
            available = self.get_available_voices()
            if voice_id not in available:
                raise TTSError(
                    f"Voice '{voice_id}' not found. "
                    f"Available voices: {len(available)}",
                )

        self._config["voice_id"] = voice_id
        voice_name = voice_id if voice_id else "default"
        self.logger.info(f"Voice set to: {voice_name}")

    def get_available_voices(self) -> List[str]:
        """
        Get list of available voice IDs.

        Returns:
            List of voice identifier strings
        """
        try:
            temp_engine = pyttsx3.init()
            voices = temp_engine.getProperty("voices")
            del temp_engine

            if voices:
                return [voice.id for voice in voices]
            return []

        except Exception as e:
            self.logger.error(f"Failed to get voices: {e}")
            return []

    def is_available(self) -> bool:
        """Check if TTS is available on this system"""
        return TTS_AVAILABLE

    def cleanup(self) -> None:
        """
        Clean up TTS resources.

        Since we create fresh engines each time, there's nothing to clean up.
        But we implement this for interface compliance.
        """
        self.logger.debug("TTS cleanup (nothing to clean with fresh engines)")
