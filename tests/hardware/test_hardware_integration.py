"""
Hardware Module Integration Tests

Focused tests following CLAUDE.md: simplicity first, top priorities only.

Tests cover:
1. Mock implementations work correctly
2. Controllers can be instantiated with mocks
3. Basic operations don't crash
4. Factory creates correct implementations
"""

import time

import pytest

# Import constants
from hardware.constants import AudioMessage
from hardware.controllers.audio_controller import AudioController

# Import controllers
from hardware.controllers.button_controller import ButtonController
from hardware.controllers.led_controller import LEDController, LEDPattern

# Import factory
from hardware.factory import HardwareFactory

# Import implementations
from hardware.implementations.mock_gpio import MockGPIO
from hardware.implementations.mock_tts import MockTTS

# Import GPIO enums
from hardware.interfaces.gpio_interface import PinState, PullMode


class TestMockImplementations:
    """Test mock implementations work correctly"""

    def test_mock_gpio_operations(self):
        """MockGPIO supports basic GPIO operations"""
        gpio = MockGPIO()

        # Setup and write
        gpio.setup_input(18, pull_mode=PullMode.UP)
        gpio.setup_output(12)
        gpio.write(12, PinState.HIGH)

        # Read
        value = gpio.read(18)
        assert value in [PinState.HIGH, PinState.LOW]

        gpio.cleanup()

    def test_mock_tts_operations(self):
        """MockTTS supports basic TTS operations"""
        tts = MockTTS(simulate_timing=False)

        # Speak and verify it was tracked
        tts.speak("Test message")
        assert "Test message" in tts.speech_history

        tts.cleanup()


class TestButtonController:
    """Test button controller basics"""

    def test_button_initialization(self):
        """Button controller initializes correctly"""
        gpio = MockGPIO()
        button = ButtonController(gpio=gpio, pin=18)

        assert button.pin == 18
        assert button.gpio == gpio

        button.cleanup()

    def test_button_with_callback(self):
        """Button can register callbacks"""
        gpio = MockGPIO()
        button = ButtonController(gpio=gpio, pin=18)

        callback_called = False

        def callback(press_type):
            nonlocal callback_called
            callback_called = True

        # Register callback using the correct method
        button.register_callback(callback)

        # Simulate press
        gpio.simulate_button_press(18)
        time.sleep(0.6)  # Wait for double-tap window + buffer

        assert callback_called
        button.cleanup()


class TestLEDController:
    """Test LED controller basics"""

    def test_led_initialization(self):
        """LED controller initializes correctly"""
        gpio = MockGPIO()
        led = LEDController(gpio=gpio)

        assert led.gpio == gpio

        led.cleanup()

    def test_led_set_status(self):
        """LED controller can set status patterns"""
        gpio = MockGPIO()
        led = LEDController(gpio=gpio)

        # Test setting patterns (should not crash)
        led.set_status(LEDPattern.OFF)
        led.set_status(LEDPattern.READY)
        led.set_status(LEDPattern.RECORDING)
        led.set_status(LEDPattern.PROCESSING)
        led.set_status(LEDPattern.ERROR)

        led.cleanup()


class TestAudioController:
    """Test audio controller basics"""

    def test_audio_initialization(self):
        """Audio controller initializes correctly"""
        tts = MockTTS(simulate_timing=False)
        audio = AudioController(tts_engine=tts)

        # Check the correct attribute name
        assert audio.tts_engine == tts

        audio.cleanup()

    def test_audio_play_message(self):
        """Audio controller can play messages"""
        tts = MockTTS(simulate_timing=False)
        audio = AudioController(tts_engine=tts)

        # Play message
        audio.play_message(AudioMessage.SYSTEM_READY)
        time.sleep(0.2)  # Let queue process

        # Verify it was spoken
        assert len(tts.speech_history) > 0

        audio.cleanup()


class TestHardwareFactory:
    """Test hardware factory"""

    def test_factory_creates_gpio_mock(self):
        """Factory creates mock GPIO"""
        gpio = HardwareFactory.create_gpio(mode="mock")

        assert isinstance(gpio, MockGPIO)
        gpio.cleanup()

    def test_factory_creates_tts_mock(self):
        """Factory creates mock TTS"""
        tts = HardwareFactory.create_tts(mode="mock")

        assert isinstance(tts, MockTTS)
        tts.cleanup()


class TestIntegration:
    """Integration tests"""

    def test_button_triggers_callback(self):
        """Button press can trigger action"""
        gpio = MockGPIO()
        button = ButtonController(gpio=gpio, pin=18)

        action_performed = False

        def on_press(press_type):
            nonlocal action_performed
            action_performed = True

        # Use the correct registration method
        button.register_callback(on_press)

        # Simulate press
        gpio.simulate_button_press(18)
        time.sleep(0.6)  # Wait for double-tap window + buffer

        assert action_performed
        button.cleanup()

    def test_audio_and_tts_integration(self):
        """Audio controller works with TTS"""
        tts = MockTTS(simulate_timing=False)
        audio = AudioController(tts_engine=tts)

        # Queue multiple messages - use correct enum values
        audio.play_message(AudioMessage.SYSTEM_READY)
        audio.play_message(
            AudioMessage.RECORDING_START,
        )  # Correct: RECORDING_START not RECORDING_STARTED

        time.sleep(0.3)  # Let queue process

        # Should have spoken both
        assert len(tts.speech_history) >= 2

        audio.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
