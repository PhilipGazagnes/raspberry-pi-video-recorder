#!/usr/bin/env python3
"""
Real Audio Hardware Test

Tests TTS audio output through actual speakers.
Run this on your computer or Raspberry Pi to verify audio works.

Usage:
    python scripts/test_audio.py
"""

import sys
import time

from hardware.constants import AudioMessage
from hardware.controllers.audio_controller import AudioController
from hardware.factory import HardwareFactory


def test_audio_system():
    """Test real TTS audio output"""
    print("=" * 60)
    print("AUDIO HARDWARE TEST")
    print("=" * 60)
    print()

    # Create real TTS engine (not mock)
    print("Initializing TTS engine...")
    try:
        tts = HardwareFactory.create_tts(mode="real")
    except Exception as e:
        print(f"ERROR: Failed to initialize TTS: {e}")
        print("\nMake sure pyttsx3 is installed: pip install pyttsx3")
        return False

    # Create audio controller
    audio = AudioController(tts_engine=tts)

    # Check system
    print("Checking audio system...")
    status = audio.check_audio_system()
    print(f"  TTS Available: {status['tts_available']}")
    print(f"  Available Voices: {status['available_voices']}")
    print(f"  Message Count: {status['message_count']}")
    print()

    if not status["tts_available"]:
        print("ERROR: TTS not available")
        audio.cleanup()
        return False

    # Test 1: Simple text
    print("Test 1: Playing simple text...")
    print("  You should hear: 'Audio test successful'")
    audio.play_text("Audio test successful")
    audio.wait_until_idle()
    time.sleep(0.5)
    print("  [OK]")
    print()

    # Test 2: Predefined messages
    print("Test 2: Playing system messages...")
    test_messages = [
        (AudioMessage.SYSTEM_READY, "System ready"),
        (AudioMessage.RECORDING_START, "Recording started"),
        (AudioMessage.ONE_MINUTE_WARNING, "One minute remaining..."),
        (AudioMessage.RECORDING_STOP, "Recording complete"),
    ]

    for msg_key, description in test_messages:
        print(f"  Playing: {description}")
        audio.play_message(msg_key)
        audio.wait_until_idle()
        time.sleep(0.3)

    print("  [OK]")
    print()

    # Test 3: Volume and rate
    print("Test 3: Testing volume and speech rate...")

    print("  Setting low volume (0.3)...")
    audio.set_volume(0.3)
    audio.play_text("This is quiet")
    audio.wait_until_idle()
    time.sleep(0.3)

    print("  Setting normal volume (0.8)...")
    audio.set_volume(0.8)
    audio.play_text("This is normal volume")
    audio.wait_until_idle()
    time.sleep(0.3)

    print("  Setting fast speech rate (200 WPM)...")
    audio.set_speech_rate(200)
    audio.play_text("This is fast speech")
    audio.wait_until_idle()
    time.sleep(0.3)

    print("  Setting slow speech rate (100 WPM)...")
    audio.set_speech_rate(100)
    audio.play_text("This is slow speech")
    audio.wait_until_idle()
    time.sleep(0.3)

    # Reset to defaults
    audio.set_volume(0.8)
    audio.set_speech_rate(125)

    print("  [OK]")
    print()

    # Test 4: Queue management
    print("Test 4: Testing message queue...")
    print("  Queuing 3 messages rapidly...")
    audio.play_text("Message one")
    audio.play_text("Message two")
    audio.play_text("Message three")

    print("  Waiting for all to complete...")
    audio.wait_until_idle()
    print("  [OK]")
    print()

    # Cleanup
    audio.cleanup()

    # Summary
    print("=" * 60)
    print("AUDIO TEST COMPLETE")
    print("=" * 60)
    print()
    print("If you heard all the test messages, audio is working correctly.")
    print()

    return True


if __name__ == "__main__":
    try:
        success = test_audio_system()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
