import logging
import queue
import subprocess
import threading
import time
from typing import Dict, Optional

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logging.warning("pyttsx3 not available - Audio controller will run in simulation mode")


class AudioController:
    """
    Handles text-to-speech audio feedback for the video recording system.
    Provides non-blocking voice prompts and status announcements.
    """

    def __init__(self, speaker_device: Optional[str] = None):
        self.speaker_device = speaker_device
        self.logger = logging.getLogger(__name__)

        # TTS engine
        self.tts_engine = None
        # Audio playback control
        self.is_playing_audio = False

        # Message queue for sequential playback
        self.message_queue = queue.Queue()
        self.queue_worker_thread = None
        self.queue_worker_running = False

        # Message library
        self.messages = self._initialize_messages()

        # Initialize TTS engine
        if TTS_AVAILABLE:
            self._setup_tts_engine()
        else:
            self.logger.warning("Running in simulation mode - no actual audio output")

        # Start queue worker thread for non-blocking playback
        self._start_queue_worker()

        self.logger.info(f"Audio Controller initialized (TTS available: {TTS_AVAILABLE})")

    def _initialize_messages(self) -> Dict[str, str]:
        """Initialize the library of voice messages"""
        return {
            # System messages
            'system_ready': "System ready",
            'system_error': "System error",
            'system_shutdown': "System shutting down",

            # Recording messages
            'recording_start': "Recording started",
            'recording_stop': "Recording complete, uploading",
            'recording_extended': "5 minutes added, recording continues",

            # Warning messages
            'one_minute_warning': "One minute remaining, press button twice to extend",
            'extension_available': "Press button twice to extend recording",

            # Status messages
            'ready_for_next': "Ready for next recording",
            'upload_complete': "Upload successful",
            'upload_failed': "Upload failed, will retry",

            # Error messages
            'memory_full': "Memory full",
            'network_disconnected': "Network disconnected",
            'camera_error': "Camera error",
            'storage_error': "Storage error",
            'upload_error': "Upload error",

            # Recovery messages
            'error_recovered': "Error resolved, system ready",
            'network_restored': "Network connection restored",
        }

    def _setup_tts_engine(self):
        """Initialize the TTS engine with proper settings"""
        try:
            # Store TTS configuration instead of keeping engine instance
            self.tts_config = {
                'voice_id': None,
                'rate': 125,
                'volume': 0.8
            }

            # Create a temporary engine to get voice configuration
            temp_engine = pyttsx3.init()
            voices = temp_engine.getProperty('voices')

            if voices:
                # Prefer female voice if available, otherwise use first voice
                for voice in voices:
                    if 'roa/fr' in voice.id:
                        self.tts_config['voice_id'] = voice.id
                        break
                else:
                    self.tts_config['voice_id'] = voices[0].id

            # Clean up temporary engine
            del temp_engine
            self.tts_engine = True  # Just a flag to indicate TTS is available

            self.logger.info("TTS engine configuration initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize TTS engine: {e}")
            self.tts_engine = None
            self.tts_config = None

    def play_message(self, message_key: str):
        """
        Play a predefined voice message (queued for sequential playback)

        Args:
            message_key: Key from the messages dictionary
        """
        if message_key not in self.messages:
            self.logger.error(f"Unknown message key: {message_key}")
            return

        message_text = self.messages[message_key]
        self.play_text(message_text)

    def play_text(self, text: str):
        """
        Play arbitrary text as speech (queued for sequential playback)

        Args:
            text: Text to speak
        """
        if not text.strip():
            self.logger.warning("Empty text provided for speech")
            return

        self.logger.info(f"Playing audio: '{text}'")

        if not TTS_AVAILABLE or not self.tts_engine:
            self.logger.info(f"[SIMULATION] Would speak: '{text}'")
            return

        # All audio is now queued for sequential playback
        self._speak_non_blocking(text)

    def _create_engine(self):
        """Create a new TTS engine with configured settings"""
        try:
            engine = pyttsx3.init()

            if self.tts_config:
                if self.tts_config['voice_id']:
                    engine.setProperty('voice', self.tts_config['voice_id'])
                engine.setProperty('rate', self.tts_config['rate'])
                engine.setProperty('volume', self.tts_config['volume'])

            # Give the engine a moment to initialize properly
            # This helps prevent cut-off beginnings
            time.sleep(0.1)

            return engine
        except Exception as e:
            self.logger.error(f"Failed to create TTS engine: {e}")
            return None

    def _start_queue_worker(self):
        """Start the background queue worker thread"""
        if not self.queue_worker_running:
            self.queue_worker_running = True
            self.queue_worker_thread = threading.Thread(
                target=self._queue_worker,
                daemon=True,
                name="AudioQueue"
            )
            self.queue_worker_thread.start()
            self.logger.debug("Queue worker thread started")

    def _queue_worker(self):
        """Background worker that processes queued messages"""
        while self.queue_worker_running:
            try:
                # Wait for a message in the queue (with timeout to check if we should stop)
                text = self.message_queue.get(timeout=1.0)

                # Process the message
                self._speak_directly(text)

                # Mark task as done
                self.message_queue.task_done()

            except queue.Empty:
                # No message in queue, continue loop to check if we should stop
                continue
            except Exception as e:
                self.logger.error(f"Error in queue worker: {e}")

    def _speak_directly(self, text: str):
        """Speak text directly (used by queue worker)"""
        try:
            self.is_playing_audio = True
            engine = self._create_engine()
            if engine:
                engine.say(text)
                time.sleep(0.05)
                engine.runAndWait()
                time.sleep(0.1)
                try:
                    engine.stop()
                except:
                    pass
                del engine
            self.is_playing_audio = False
        except Exception as e:
            self.logger.error(f"Error in direct speech: {e}")
            self.is_playing_audio = False

    def _speak_non_blocking(self, text: str):
        """Speak text using message queue for sequential playback"""
        # Add message to queue - it will be processed by the queue worker
        self.message_queue.put(text)
        self.logger.debug(f"Added message to queue: '{text[:20]}...'")

    # Remove the old _playback_worker method - we don't need it anymore

    def stop_playback(self):
        """Stop any current audio playback and clear queue"""
        # Clear the message queue
        self.clear_queue()

        # Set flag to stop current playback
        self.is_playing_audio = False
        self.logger.debug("Audio playback stopped and queue cleared")

    def clear_queue(self):
        """Clear all pending messages from the queue"""
        try:
            while not self.message_queue.empty():
                self.message_queue.get_nowait()
                self.message_queue.task_done()
            self.logger.debug("Message queue cleared")
        except queue.Empty:
            pass

    def get_queue_size(self) -> int:
        """Get the number of messages waiting in the queue"""
        return self.message_queue.qsize()

    def is_playing(self) -> bool:
        """Check if audio is currently playing or if there are queued messages"""
        return self.is_playing_audio or not self.message_queue.empty()

    def set_volume(self, volume: float):
        """
        Set TTS volume

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        if not (0.0 <= volume <= 1.0):
            self.logger.error(f"Invalid volume level: {volume}. Must be between 0.0 and 1.0")
            return

        if self.tts_config:
            try:
                self.tts_config['volume'] = volume
                self.logger.info(f"Volume set to {volume}")
            except Exception as e:
                self.logger.error(f"Error setting volume: {e}")

    def set_speech_rate(self, rate: int):
        """
        Set TTS speech rate

        Args:
            rate: Words per minute (typical range: 100-300)
        """
        if not (50 <= rate <= 400):
            self.logger.error(f"Invalid speech rate: {rate}. Typical range is 100-300 WPM")
            return

        if self.tts_config:
            try:
                self.tts_config['rate'] = rate
                self.logger.info(f"Speech rate set to {rate} WPM")
            except Exception as e:
                self.logger.error(f"Error setting speech rate: {e}")

    def test_audio(self):
        """Test audio functionality with a sample message"""
        self.logger.info("Starting audio test")

        if not TTS_AVAILABLE:
            self.logger.info("Audio test: TTS not available, running in simulation mode")
            self.play_text("This is an audio test message")
            return

        # Test basic functionality - all messages are queued sequentially
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
        while self.is_playing():
            time.sleep(0.1)

        self.logger.info("Audio test complete")

    def test_all_messages(self):
        """Test all predefined messages"""
        self.logger.info("Testing all predefined messages")

        for key, message in self.messages.items():
            self.logger.info(f"Testing message '{key}': {message}")
            self.play_message(key)

        # Wait for all messages to complete
        while self.is_playing():
            time.sleep(0.1)

        self.logger.info("All message tests complete")

    def add_custom_message(self, key: str, message: str):
        """
        Add a custom message to the message library

        Args:
            key: Unique identifier for the message
            message: Text to speak
        """
        self.messages[key] = message
        self.logger.info(f"Added custom message '{key}': {message}")

    def get_message_keys(self) -> list:
        """Get list of available message keys"""
        return list(self.messages.keys())

    def check_audio_system(self) -> dict:
        """Check audio system health and capabilities"""
        status = {
            'tts_available': TTS_AVAILABLE,
            'engine_initialized': self.tts_engine is not None,
            'currently_playing': self.is_playing_audio,
            'speaker_device': self.speaker_device,
            'message_count': len(self.messages)
        }

        if self.tts_config:
            try:
                # Test engine creation to get system info
                temp_engine = pyttsx3.init()
                voices = temp_engine.getProperty('voices')
                status['available_voices'] = len(voices) if voices else 0
                status['current_rate'] = self.tts_config['rate']
                status['current_volume'] = self.tts_config['volume']
                del temp_engine
            except Exception as e:
                status['engine_error'] = str(e)

        return status

    def get_status(self) -> dict:
        """Get current audio controller status"""
        return {
            'tts_available': TTS_AVAILABLE,
            'engine_ready': self.tts_engine is not None,
            'is_playing': self.is_playing_audio,
            'queue_size': self.get_queue_size(),
            'message_library_size': len(self.messages),
            'speaker_device': self.speaker_device
        }

    def cleanup(self):
        """Clean up audio resources"""
        self.logger.info("Cleaning up Audio Controller")

        # Stop queue worker
        self.queue_worker_running = False
        if self.queue_worker_thread and self.queue_worker_thread.is_alive():
            self.queue_worker_thread.join(timeout=2.0)

        # Stop any current playback
        self.stop_playback()

        # Clear configuration
        self.tts_engine = None
        self.tts_config = None

        self.logger.info("Audio Controller cleanup complete")

    def __del__(self):
        """Destructor - ensure cleanup"""
        self.cleanup()
