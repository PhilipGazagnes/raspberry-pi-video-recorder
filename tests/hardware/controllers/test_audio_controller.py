"""
Audio Controller Tests

Tests for the audio controller showing:
- Message playback
- TTS configuration
- Component integration
- High-level API

To run these tests:
    pytest tests/hardware/controllers/test_audio_controller.py -v
"""

import time

import pytest

from hardware.constants import AudioMessage
from hardware.controllers.audio_controller import AudioController


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================

@pytest.mark.unit
def test_audio_controller_initialization(mock_tts_fast):
    """
    Test audio controller initializes correctly.

    Should:
    - Initialize TTS engine
    - Load message library
    - Start audio queue
    """
    audio = AudioController(tts_engine=mock_tts_fast)

    # Check status
    status = audio.get_status()
    assert status['tts_available'] is True
    assert status['message_library']['total'] > 0
    assert status['queue']['worker_running'] is True

    audio.cleanup()


# =============================================================================
# MESSAGE PLAYBACK TESTS
# =============================================================================

@pytest.mark.unit
def test_audio_play_message(audio_controller, mock_tts_fast):
    """
    Test playing a predefined message by key.

    Should queue message and play via TTS.
    """
    # Play message
    audio_controller.play_message(AudioMessage.RECORDING_START)

    # Wait for playback
    audio_controller.wait_until_idle()

    # Should have been spoken
    assert mock_tts_fast.was_spoken("Recording started")


@pytest.mark.unit
def test_audio_play_multiple_messages(audio_controller, mock_tts_fast):
    """
    Test playing multiple messages in sequence.

    Messages should play in order.
    """
    # Queue several messages
    audio_controller.play_message(AudioMessage.SYSTEM_READY)
    audio_controller.play_message(AudioMessage.RECORDING_START)
    audio_controller.play_message(AudioMessage.RECORDING_STOP)

    # Wait for all
    audio_controller.wait_until_idle()

    # Check history
    history = mock_tts_fast.get_speech_history()
    assert len(history) == 3
    assert "System ready" in history[0]
    assert "Recording started" in history[1]
    assert "Recording complete" in history[2]


@pytest.mark.unit
def test_audio_play_text(audio_controller, mock_tts_fast):
    """
    Test playing arbitrary text.

    Should queue and play custom text.
    """
    # Play custom text
    audio_controller.play_text("This is a custom message")

    # Wait
    audio_controller.wait_until_idle()

    # Should have been spoken
    assert mock_tts_fast.was_spoken("This is a custom message")


@pytest.mark.unit
def test_audio_play_text_empty_ignored(audio_controller, mock_tts_fast):
    """
    Test that empty text is ignored.
    """
    # Try empty text
    audio_controller.play_text("")
    audio_controller.play_text("   ")

    time.sleep(0.2)

    # Nothing should be spoken
    assert len(mock_tts_fast.get_speech_history()) == 0


# =============================================================================
# QUEUE CONTROL TESTS
# =============================================================================

@pytest.mark.unit
def test_audio_stop_playback(mock_tts_fast):
    """
    Test stopping playback and clearing queue.

    Should clear pending messages.
    """
    # Use realistic timing so messages don't complete instantly
    mock_tts_realistic = type(mock_tts_fast)(simulate_timing=True)
    audio = AudioController(tts_engine=mock_tts_realistic)

    # Queue several messages
    audio.play_text("Message 1")
    audio.play_text("Message 2")
    audio.play_text("Message 3")

    time.sleep(0.1)  # Let first start

    # Stop playback
    audio.stop_playback()

    # Wait a moment
    time.sleep(0.5)

    # Only first message should have played
    history = mock_tts_realistic.get_speech_history()
    assert len(history) <= 2  # First + maybe second if it started

    audio.cleanup()


@pytest.mark.unit
def test_audio_is_playing(audio_controller, mock_tts_fast):
    """
    Test is_playing() status.
    """
    # Initially not playing
    assert audio_controller.is_playing() is False

    # Play message (with realistic timing)
    mock_tts_realistic = type(mock_tts_fast)(simulate_timing=True)
    audio2 = AudioController(tts_engine=mock_tts_realistic)

    audio2.play_text("Test message")
    time.sleep(0.1)

    # Should be playing
    assert audio2.is_playing() is True

    # Wait for completion
    audio2.wait_until_idle()

    # Should be done
    assert audio2.is_playing() is False

    audio2.cleanup()


@pytest.mark.unit
def test_audio_is_busy(audio_controller, mock_tts_fast):
    """
    Test is_busy() status (playing or queued).
    """
    # Initially not busy
    assert audio_controller.is_busy() is False

    # Use realistic timing
    mock_tts_realistic = type(mock_tts_fast)(simulate_timing=True)
    audio2 = AudioController(tts_engine=mock_tts_realistic)

    # Queue messages
    audio2.play_text("Message 1")
    audio2.play_text("Message 2")

    # Should be busy
    assert audio2.is_busy() is True

    # Wait for completion
    audio2.wait_until_idle()

    # Should not be busy
    assert audio2.is_busy() is False

    audio2.cleanup()


# =============================================================================
# TTS CONFIGURATION TESTS
# =============================================================================

@pytest.mark.unit
def test_audio_set_volume(audio_controller, mock_tts_fast):
    """
    Test setting TTS volume.

    Should update TTS engine configuration.
    """
    # Set volume
    audio_controller.set_volume(0.5)

    # Check TTS configuration
    config = mock_tts_fast.get_config()
    assert config['volume'] == 0.5


@pytest.mark.unit
def test_audio_set_speech_rate(audio_controller, mock_tts_fast):
    """
    Test setting speech rate.
    """
    # Set rate
    audio_controller.set_speech_rate(200)

    # Check TTS configuration
    config = mock_tts_fast.get_config()
    assert config['rate'] == 200


# =============================================================================
# MESSAGE LIBRARY INTEGRATION TESTS
# =============================================================================

@pytest.mark.unit
def test_audio_add_custom_message(audio_controller, mock_tts_fast):
    """
    Test adding custom message through controller.

    Should update message library.
    """
    # Add custom message
    audio_controller.add_custom_message(
        AudioMessage.SYSTEM_READY,
        "Custom ready message"
    )

    # Play it
    audio_controller.play_message(AudioMessage.SYSTEM_READY)
    audio_controller.wait_until_idle()

    # Should play custom version
    assert mock_tts_fast.was_spoken("Custom ready message")


@pytest.mark.unit
def test_audio_get_available_messages(audio_controller):
    """
    Test getting list of available messages.
    """
    messages = audio_controller.get_available_messages()

    # Should have messages
    assert len(messages) > 0

    # Should include known messages
    assert AudioMessage.RECORDING_START in messages
    assert AudioMessage.SYSTEM_READY in messages


# =============================================================================
# STATUS AND DIAGNOSTICS TESTS
# =============================================================================

@pytest.mark.unit
def test_audio_get_status(audio_controller):
    """
    Test get_status() returns complete information.
    """
    status = audio_controller.get_status()

    # Should have all sections
    assert 'tts_available' in status
    assert 'message_library' in status
    assert 'queue' in status

    # Message library should have counts
    assert 'default' in status['message_library']
    assert 'custom' in status['message_library']
    assert 'total' in status['message_library']


@pytest.mark.unit
def test_audio_check_audio_system(audio_controller):
    """
    Test check_audio_system() diagnostics.
    """
    info = audio_controller.check_audio_system()

    # Should have system info
    assert 'tts_available' in info
    assert 'message_count' in info
    assert 'queue_size' in info
    assert 'is_playing' in info


# =============================================================================
# TESTING METHODS TESTS
# =============================================================================

@pytest.mark.unit
def test_audio_test_audio(mock_tts_fast):
    """
    Test the test_audio() method.

    Should play several test messages.
    """
    audio = AudioController(tts_engine=mock_tts_fast)

    # Run test
    audio.test_audio()

    # Should have spoken test messages
    history = mock_tts_fast.get_speech_history()
    assert len(history) >= 3  # Several test messages

    audio.cleanup()


@pytest.mark.unit
@pytest.mark.slow
def test_audio_test_all_messages(mock_tts_fast):
    """
    Test the test_all_messages() method.

    Should play all messages in library.
    Note: Marked as slow since it plays many messages.
    """
    audio = AudioController(tts_engine=mock_tts_fast)

    # Run test
    audio.test_all_messages()

    # Should have spoken many messages
    history = mock_tts_fast.get_speech_history()
    assert len(history) > 10  # Should have many default messages

    audio.cleanup()


# =============================================================================
# CLEANUP TESTS
# =============================================================================

@pytest.mark.unit
def test_audio_cleanup(mock_tts_fast):
    """
    Test cleanup properly releases resources.

    Should:
    - Stop audio queue
    - Clean up TTS engine
    """
    audio = AudioController(tts_engine=mock_tts_fast)

    # Queue something
    audio.play_text("Test")

    # Cleanup
    audio.cleanup()

    # Queue should be stopped
    status = audio.get_status()
    assert status['queue']['worker_running'] is False


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

@pytest.mark.unit_integration
def test_audio_complete_workflow(mock_tts_fast):
    """
    Integration test: Complete audio system workflow.

    Simulates real system usage.
    """
    audio = AudioController(tts_engine=mock_tts_fast)

    # System startup
    audio.play_message(AudioMessage.SYSTEM_READY)
    audio.wait_until_idle()

    # Start recording
    audio.play_message(AudioMessage.RECORDING_START)
    audio.wait_until_idle()

    # Warning
    audio.play_message(AudioMessage.ONE_MINUTE_WARNING)
    audio.wait_until_idle()

    # Extension
    audio.play_message(AudioMessage.RECORDING_EXTENDED)
    audio.wait_until_idle()

    # Stop and process
    audio.play_message(AudioMessage.RECORDING_STOP)
    audio.wait_until_idle()

    # Complete
    audio.play_message(AudioMessage.UPLOAD_COMPLETE)
    audio.play_message(AudioMessage.READY_FOR_NEXT)
    audio.wait_until_idle()

    # Verify all were spoken
    history = mock_tts_fast.get_speech_history()
    assert len(history) == 7

    audio.cleanup()


@pytest.mark.unit_integration
def test_audio_mixed_messages_and_text(mock_tts_fast):
    """
    Integration test: Mix of predefined messages and custom text.
    """
    audio = AudioController(tts_engine=mock_tts_fast)

    # Mix predefined and custom
    audio.play_message(AudioMessage.SYSTEM_READY)
    audio.play_text("Initializing camera")
    audio.play_text("Camera ready")
    audio.play_message(AudioMessage.RECORDING_START)
    audio.play_text("Recording to file recording_001.mp4")

    # Wait for all
    audio.wait_until_idle()

    # All should be spoken
    history = mock_tts_fast.get_speech_history()
    assert len(history) == 5

    audio.cleanup()


@pytest.mark.unit_integration
def test_audio_error_recovery(mock_tts_fast):
    """
    Integration test: System handles TTS errors gracefully.
    """
    audio = AudioController(tts_engine=mock_tts_fast)

    # Make one message fail
    original_speak = mock_tts_fast.speak
    call_count = [0]

    def sometimes_fail_speak(text):
        call_count[0] += 1
        if call_count[0] == 2:  # Fail on second call
            raise RuntimeError("Simulated TTS error")
        original_speak(text)

    mock_tts_fast.speak = sometimes_fail_speak

    # Play several messages
    audio.play_text("Message 1")
    audio.play_text("Message 2")  # This will fail
    audio.play_text("Message 3")

    # Wait
    audio.wait_until_idle()

    # First and third should have played
    # (Second failed but didn't crash the system)
    history = mock_tts_fast.get_speech_history()
    assert "Message 1" in history
    assert "Message 3" in history

    # Restore
    mock_tts_fast.speak = original_speak

    audio.cleanup()


@pytest.mark.unit_integration
def test_audio_configuration_persistence(mock_tts_fast):
    """
    Test that TTS configuration persists across messages.
    """
    audio = AudioController(tts_engine=mock_tts_fast)

    # Configure
    audio.set_volume(0.7)
    audio.set_speech_rate(180)

    # Play messages
    audio.play_text("First message")
    audio.wait_until_idle()

    # Check config still applied
    config = mock_tts_fast.get_config()
    assert config['volume'] == 0.7
    assert config['rate'] == 180

    # Play more
    audio.play_text("Second message")
    audio.wait_until_idle()

    # Still configured
    config2 = mock_tts_fast.get_config()
    assert config2['volume'] == 0.7
    assert config2['rate'] == 180

    audio.cleanup()
