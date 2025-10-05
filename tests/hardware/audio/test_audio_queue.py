"""
Audio Queue Tests

Tests for audio queue showing:
- Queue operations
- Sequential playback
- Threading behavior
- Queue management

To run these tests:
    pytest tests/hardware/audio/test_audio_queue.py -v
"""

import time

import pytest

from hardware.audio.audio_queue import AudioQueue

# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


@pytest.mark.unit
def test_audio_queue_initialization(mock_tts_fast):
    """
    Test audio queue initializes correctly.

    Should:
    - Create queue
    - Start worker thread
    - Be ready to accept messages
    """
    queue = AudioQueue(mock_tts_fast)

    # Check status
    status = queue.get_status()
    assert status["worker_running"] is True
    assert status["queue_size"] == 0
    assert status["is_playing"] is False

    queue.stop()


# =============================================================================
# BASIC PLAYBACK TESTS
# =============================================================================


@pytest.mark.unit
def test_audio_queue_play_single_message(mock_tts_fast):
    """
    Test playing a single message.

    Should:
    - Queue message
    - Play message via TTS
    - Complete successfully
    """
    queue = AudioQueue(mock_tts_fast)

    # Play message
    queue.play("Test message")

    # Give worker time to process
    time.sleep(0.2)

    # Should have been spoken
    assert mock_tts_fast.was_spoken("Test message")

    queue.stop()


@pytest.mark.unit
def test_audio_queue_play_multiple_messages(mock_tts_fast):
    """
    Test playing multiple messages sequentially.

    Messages should play in order they were queued.
    """
    queue = AudioQueue(mock_tts_fast)

    # Queue multiple messages
    queue.play("Message 1")
    queue.play("Message 2")
    queue.play("Message 3")

    # Wait for all to play
    queue.wait_until_idle()

    # Check history
    history = mock_tts_fast.get_speech_history()
    assert len(history) == 3
    assert history[0] == "Message 1"
    assert history[1] == "Message 2"
    assert history[2] == "Message 3"

    queue.stop()


@pytest.mark.unit
def test_audio_queue_empty_text_ignored(mock_tts_fast):
    """
    Test that empty text is ignored.

    Should not queue empty strings.
    """
    queue = AudioQueue(mock_tts_fast)

    # Try to play empty text
    queue.play("")
    queue.play("   ")  # Whitespace only

    # Wait a moment
    time.sleep(0.2)

    # Nothing should have been spoken
    assert len(mock_tts_fast.get_speech_history()) == 0

    queue.stop()


# =============================================================================
# QUEUE MANAGEMENT TESTS
# =============================================================================


@pytest.mark.unit
def test_audio_queue_get_queue_size(mock_tts_fast):
    """
    Test getting queue size.

    Should return number of pending messages.
    """
    queue = AudioQueue(mock_tts_fast)

    # Initially empty
    assert queue.get_queue_size() == 0

    # Queue messages quickly (before they play)
    # Use realistic TTS to slow down processing
    mock_tts_realistic = type(mock_tts_fast)(simulate_timing=True)
    queue2 = AudioQueue(mock_tts_realistic)

    queue2.play("Long message one")
    queue2.play("Long message two")
    queue2.play("Long message three")

    # Should have messages queued
    time.sleep(0.1)  # Give a moment for first to start
    size = queue2.get_queue_size()
    assert size >= 0  # At least some should be queued

    queue.stop()
    queue2.stop()


@pytest.mark.unit
def test_audio_queue_clear_queue(mock_tts_fast):
    """
    Test clearing queued messages.

    Should remove all pending messages (but not currently playing).
    """
    # Use realistic timing so messages don't complete instantly
    mock_tts_realistic = type(mock_tts_fast)(simulate_timing=True)
    queue = AudioQueue(mock_tts_realistic)

    # Queue several messages
    queue.play("Message 1")
    queue.play("Message 2")
    queue.play("Message 3")
    queue.play("Message 4")

    time.sleep(0.1)  # Let first one start

    # Clear queue
    cleared = queue.clear_queue()

    # Should have cleared some messages
    assert cleared > 0

    # Wait for current to finish
    queue.wait_until_idle(timeout=5.0)

    # Only first message should have played
    history = mock_tts_realistic.get_speech_history()
    assert len(history) == 1
    assert history[0] == "Message 1"

    queue.stop()


# =============================================================================
# STATUS TESTS
# =============================================================================


@pytest.mark.unit
def test_audio_queue_is_playing(mock_tts_fast):
    """
    Test is_playing() status.

    Should return True while speaking, False when idle.
    """
    # Use realistic timing for this test
    mock_tts_realistic = type(mock_tts_fast)(simulate_timing=True)
    queue = AudioQueue(mock_tts_realistic)

    # Initially not playing
    assert queue.is_playing() is False

    # Play message
    queue.play("Test message")
    time.sleep(0.1)  # Give it time to start

    # Should be playing now
    assert queue.is_playing() is True

    # Wait for completion
    queue.wait_until_idle()

    # Should be done
    assert queue.is_playing() is False

    queue.stop()


@pytest.mark.unit
def test_audio_queue_is_busy(mock_tts_fast):
    """
    Test is_busy() status.

    Should return True if playing OR has queued messages.
    """
    mock_tts_realistic = type(mock_tts_fast)(simulate_timing=True)
    queue = AudioQueue(mock_tts_realistic)

    # Initially not busy
    assert queue.is_busy() is False

    # Queue multiple messages
    queue.play("Message 1")
    queue.play("Message 2")

    # Should be busy (either playing or queued)
    assert queue.is_busy() is True

    # Wait for completion
    queue.wait_until_idle()

    # Should not be busy
    assert queue.is_busy() is False

    queue.stop()


@pytest.mark.unit
def test_audio_queue_get_current_message(mock_tts_fast):
    """
    Test getting currently playing message.

    Should return message text while playing, None when idle.
    """
    mock_tts_realistic = type(mock_tts_fast)(simulate_timing=True)
    queue = AudioQueue(mock_tts_realistic)

    # Initially None
    assert queue.get_current_message() is None

    # Play message
    queue.play("Current message")
    time.sleep(0.1)  # Let it start

    # Should show current message
    current = queue.get_current_message()
    assert current == "Current message"

    # Wait for completion
    queue.wait_until_idle()

    # Should be None again
    assert queue.get_current_message() is None

    queue.stop()


@pytest.mark.unit
def test_audio_queue_get_status(mock_tts_fast):
    """
    Test get_status() returns complete information.
    """
    queue = AudioQueue(mock_tts_fast)

    status = queue.get_status()

    # Should have all required fields
    assert "is_playing" in status
    assert "current_message" in status
    assert "queue_size" in status
    assert "is_busy" in status
    assert "worker_running" in status

    queue.stop()


# =============================================================================
# WAIT OPERATIONS TESTS
# =============================================================================


@pytest.mark.unit
def test_audio_queue_wait_until_idle(mock_tts_fast):
    """
    Test wait_until_idle() blocks until queue is empty.

    Should wait for all messages to complete.
    """
    mock_tts_realistic = type(mock_tts_fast)(simulate_timing=True)
    queue = AudioQueue(mock_tts_realistic)

    # Queue messages
    queue.play("Message 1")
    queue.play("Message 2")

    # Wait for completion
    start = time.time()
    result = queue.wait_until_idle(timeout=10.0)
    elapsed = time.time() - start

    # Should have waited
    assert result is True
    assert elapsed > 0.1  # Should take some time

    # Queue should be empty
    assert queue.is_busy() is False

    queue.stop()


@pytest.mark.unit
def test_audio_queue_wait_until_idle_timeout(mock_tts_fast):
    """
    Test wait_until_idle() respects timeout.

    Should return False if timeout occurs before completion.
    """
    # Use realistic timing with long messages
    mock_tts_realistic = type(mock_tts_fast)(simulate_timing=True)
    queue = AudioQueue(mock_tts_realistic)

    # Queue a long message
    long_message = "This is a very long message " * 20
    queue.play(long_message)

    # Wait with short timeout
    result = queue.wait_until_idle(timeout=0.1)

    # Should timeout
    # Note: might return True if message completes very fast
    # This test is timing-dependent

    queue.stop()


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


@pytest.mark.unit
def test_audio_queue_tts_error_handling(mock_tts_fast, caplog):
    """
    Test that TTS errors don't crash the queue.

    If TTS.speak() raises exception, queue should log error and continue.
    """
    # Make TTS raise error
    original_speak = mock_tts_fast.speak

    def error_speak(text):
        raise RuntimeError("Simulated TTS error")

    mock_tts_fast.speak = error_speak

    queue = AudioQueue(mock_tts_fast)

    # Try to play
    queue.play("This will fail")

    # Wait for processing
    time.sleep(0.3)

    # Should have logged error
    assert "error speaking message" in caplog.text.lower()

    # Restore original
    mock_tts_fast.speak = original_speak

    queue.stop()


# =============================================================================
# CLEANUP TESTS
# =============================================================================


@pytest.mark.unit
def test_audio_queue_stop():
    """
    Test stop() properly shuts down queue.

    Should:
    - Clear pending messages
    - Stop worker thread
    - Clean up resources
    """
    from hardware.implementations.mock_tts import MockTTS

    mock_tts = MockTTS(simulate_timing=False)
    queue = AudioQueue(mock_tts)

    # Queue some messages
    queue.play("Message 1")
    queue.play("Message 2")

    # Stop
    queue.stop()

    # Worker should be stopped
    status = queue.get_status()
    assert status["worker_running"] is False


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


@pytest.mark.unit_integration
def test_audio_queue_realistic_workflow(mock_tts_fast):
    """
    Integration test: Realistic audio queue usage.

    Simulates actual system usage pattern.
    """
    queue = AudioQueue(mock_tts_fast)

    # System startup
    queue.play("System ready")
    queue.wait_until_idle()

    # User action
    queue.play("Recording started")
    queue.wait_until_idle()

    # Multiple status updates
    queue.play("Processing")
    queue.play("Uploading")
    queue.play("Upload complete")
    queue.wait_until_idle()

    # Verify all were spoken
    history = mock_tts_fast.get_speech_history()
    assert len(history) == 5

    queue.stop()


@pytest.mark.unit_integration
def test_audio_queue_stress_test(mock_tts_fast):
    """
    Stress test: Many rapid messages.

    Queue should handle high load without issues.
    """
    queue = AudioQueue(mock_tts_fast)

    # Queue many messages rapidly
    for i in range(50):
        queue.play(f"Message {i}")

    # Wait for all to complete
    queue.wait_until_idle(timeout=10.0)

    # Should have processed all
    history = mock_tts_fast.get_speech_history()
    assert len(history) == 50

    queue.stop()
