"""
Audio Queue

Manages sequential audio playback using a queue and worker thread.
This is extracted from AudioController following Single Responsibility Principle.

Why a queue?
- Prevents overlapping speech (one message at a time)
- Non-blocking operation (returns immediately, plays in background)
- Natural message ordering (first queued, first played)

SOLID Principles:
- Single Responsibility: Only manages audio playback queue
- Dependency Inversion: Depends on TTSInterface, not specific TTS engine
"""

import logging
import queue
import threading
from typing import Any, Dict, Optional

from hardware.interfaces.tts_interface import TTSInterface


class AudioQueue:
    """
    Sequential audio playback queue.

    This class:
    - Maintains a FIFO queue of messages
    - Runs a background worker thread
    - Plays messages one at a time
    - Provides queue status information

    Usage:
        tts = create_tts()
        audio_queue = AudioQueue(tts)
        audio_queue.play("Hello")  # Returns immediately
        audio_queue.play("World")  # Queued, plays after "Hello"
    """

    def __init__(self, tts_engine: TTSInterface):
        """
        Initialize audio queue.

        Args:
            tts_engine: TTS interface for speech synthesis

        Example:
            tts = create_tts()
            audio_queue = AudioQueue(tts)
        """
        self.logger = logging.getLogger(__name__)
        self.tts_engine = tts_engine

        # Message queue (thread-safe FIFO)
        # queue.Queue is thread-safe - can add/remove from multiple threads
        self._message_queue: queue.Queue[str] = queue.Queue()

        # Worker thread control
        self._worker_thread: Optional[threading.Thread] = None
        self._worker_running = False

        # Playback state
        self._is_playing = False
        self._current_message: Optional[str] = None

        # Start worker thread
        self._start_worker()

        self.logger.info("Audio Queue initialized")

    def _start_worker(self) -> None:
        """
        Start the background worker thread.

        The worker thread:
        1. Waits for messages in queue
        2. Speaks each message using TTS
        3. Continues until stopped

        This runs in the background, so play() returns immediately.
        """
        if self._worker_running:
            self.logger.warning("Worker already running")
            return

        self._worker_running = True
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,  # Dies when main program exits
            name="AudioQueue-Worker",
        )
        self._worker_thread.start()

        self.logger.debug("Audio queue worker started")

    def _worker_loop(self) -> None:
        """
        Background worker thread that processes the queue.

        This runs continuously:
        1. Wait for message in queue (blocks until available)
        2. Speak the message (blocks until complete)
        3. Repeat

        The queue.get() with timeout allows us to check if we should stop.
        """
        self.logger.debug("Worker thread started")

        while self._worker_running:
            try:
                # WHY use queue.get(timeout=1.0)?
                # Context: We need to be able to stop the worker thread when
                #   shutdown() is called. Without a timeout, queue.get() blocks
                #   forever waiting for a message, and we can't check
                #   _worker_running flag.
                #
                # Why 1.0 seconds?
                #   - Too short (0.1s): Wastes CPU checking flag repeatedly,
                #     more context switches
                #   - Too long (10s): Shutdown takes too long when worker is
                #     idle
                #   - 1.0s: Good balance - responsive shutdown, minimal CPU
                #     waste
                #
                # Pattern: This is a standard "cooperative shutdown" pattern
                #   with queues. When no message available, Empty exception
                #   fires, we loop back and check flag. When message available,
                #   we wake up immediately (don't wait full 1s).
                text = self._message_queue.get(timeout=1.0)

                # We have a message - speak it
                self._speak_message(text)

                # WHY call task_done()?
                # Context: queue.join() blocks until all items are "done".
                #   Callers use wait_until_idle() to know when all queued
                #   messages finished playing. Without task_done(),
                #   wait_until_idle() would hang forever.
                self._message_queue.task_done()

            except queue.Empty:
                # No message in queue within timeout window - loop continues
                # to check if we should stop
                continue
            except Exception as e:
                # Never let worker crash - just log and continue
                # This prevents one bad message from killing the entire audio
                # system
                self.logger.error(f"Error in worker loop: {e}", exc_info=True)

        self.logger.debug("Worker thread stopped")

    def _speak_message(self, text: str) -> None:
        """
        Speak a single message.

        This is called by the worker thread for each queued message.
        It's BLOCKING - doesn't return until speech finishes.

        Args:
            text: Text to speak
        """
        try:
            self._is_playing = True
            self._current_message = text

            self.logger.debug(f"Speaking: '{text[:30]}...'")

            # This blocks until speech completes
            self.tts_engine.speak(text)

        except Exception as e:
            self.logger.error(f"Error speaking message: {e}", exc_info=True)
        finally:
            self._is_playing = False
            self._current_message = None

    def play(self, text: str) -> None:
        """
        Queue text for speech playback.

        This returns IMMEDIATELY - speech happens in background.
        Messages are played in order they're queued.

        Args:
            text: Text to speak

        Example:
            audio_queue.play("First message")
            audio_queue.play("Second message")  # Plays after first completes
            # Function returns immediately, speech plays in background
        """
        if not text.strip():
            self.logger.warning("Empty text provided, ignoring")
            return

        # Add to queue - worker thread will process it
        self._message_queue.put(text)

        self.logger.debug(
            f"Queued message: '{text[:30]}...' "
            f"(queue size: {self.get_queue_size()})",
        )

    def clear_queue(self) -> int:
        """
        Clear all pending messages from queue.

        Note: Cannot stop currently playing message, only clears pending ones.

        Returns:
            Number of messages that were cleared

        Example:
            # Oh no, cancel everything!
            cleared = audio_queue.clear_queue()
            print(f"Cleared {cleared} messages")
        """
        cleared_count = 0

        try:
            while True:
                self._message_queue.get_nowait()
                self._message_queue.task_done()
                cleared_count += 1
        except queue.Empty:
            # Queue is now empty
            pass

        if cleared_count > 0:
            self.logger.info(f"Cleared {cleared_count} queued messages")

        return cleared_count

    def get_queue_size(self) -> int:
        """
        Get number of messages waiting in queue.

        Does NOT include currently playing message.

        Returns:
            Number of pending messages

        Example:
            if audio_queue.get_queue_size() > 5:
                print("Queue is getting long!")
        """
        return self._message_queue.qsize()

    def is_playing(self) -> bool:
        """
        Check if audio is currently playing.

        Returns:
            True if speaking now, False if idle

        Example:
            while audio_queue.is_playing():
                time.sleep(0.1)  # Wait for speech to finish
        """
        return self._is_playing

    def is_busy(self) -> bool:
        """
        Check if queue is playing OR has pending messages.

        Returns:
            True if any audio activity (playing or queued)

        Example:
            if not audio_queue.is_busy():
                print("Audio system is idle")
        """
        return self._is_playing or not self._message_queue.empty()

    def get_current_message(self) -> Optional[str]:
        """
        Get currently playing message.

        Returns:
            Message text if playing, None if idle

        Example:
            current = audio_queue.get_current_message()
            if current:
                print(f"Now playing: {current}")
        """
        return self._current_message

    def wait_until_idle(self, timeout: Optional[float] = None) -> bool:
        """
        Wait until all queued messages have been played.

        Blocks until queue is empty and nothing is playing.

        Args:
            timeout: Maximum time to wait in seconds, or None for no limit

        Returns:
            True if queue became idle, False if timeout occurred

        Example:
            # Play messages and wait for completion
            audio_queue.play("Message 1")
            audio_queue.play("Message 2")
            audio_queue.wait_until_idle()  # Blocks until both are spoken
            print("All done!")
        """
        try:
            # Wait for queue to empty
            if timeout:
                self._message_queue.join()
                # Additional check for is_playing
                import time

                start = time.time()
                while self._is_playing and (time.time() - start) < timeout:
                    time.sleep(0.1)
                return not self._is_playing
            self._message_queue.join()
            # Wait for current message to finish
            import time

            while self._is_playing:
                time.sleep(0.1)
            return True
        except Exception as e:
            self.logger.error(f"Error waiting for idle: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """
        Get detailed queue status.

        Returns:
            Dictionary with queue information

        Example:
            status = audio_queue.get_status()
            print(f"Queue size: {status['queue_size']}")
            print(f"Is playing: {status['is_playing']}")
        """
        return {
            "is_playing": self._is_playing,
            "current_message": self._current_message,
            "queue_size": self.get_queue_size(),
            "is_busy": self.is_busy(),
            "worker_running": self._worker_running,
        }

    def stop(self) -> None:
        """
        Stop the worker thread and clear queue.

        Call this when shutting down the audio system.

        Example:
            audio_queue.stop()
        """
        self.logger.info("Stopping audio queue")

        # Clear pending messages
        self.clear_queue()

        # Stop worker thread
        self._worker_running = False

        # Wait for worker to finish current message
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=3.0)

        self.logger.info("Audio queue stopped")

    def __del__(self):
        """Destructor - ensure worker is stopped"""
        self.stop()
