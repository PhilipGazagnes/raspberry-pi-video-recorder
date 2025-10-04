"""
Test Configuration and Fixtures

This file contains pytest fixtures that are shared across multiple test files.
Fixtures are reusable test setup/teardown code.

Why use fixtures?
- DRY: Setup code in one place
- Automatic cleanup: Fixtures handle teardown
- Composable: Fixtures can use other fixtures
- Clear dependencies: Test signature shows what it needs

To use pytest:
    pip install pytest
    pytest tests/hardware/
"""

import pytest

from hardware.implementations.mock_gpio import MockGPIO
from hardware.implementations.mock_tts import MockTTS


# =============================================================================
# GPIO FIXTURES
# =============================================================================

@pytest.fixture
def mock_gpio():
    """
    Provide a fresh MockGPIO instance for each test.

    This is a "function-scoped" fixture (default) - creates new instance per test.
    Ensures tests don't interfere with each other.

    Usage in test:
        def test_something(mock_gpio):
            mock_gpio.setup_output(12)
            # ... test code ...
    """
    gpio = MockGPIO()
    yield gpio  # Test runs here
    # Cleanup after test
    gpio.cleanup()


@pytest.fixture
def configured_gpio(mock_gpio):
    """
    Provide a MockGPIO with LED pins already configured.

    This is a "derived fixture" - builds on mock_gpio fixture.
    Useful when many tests need the same setup.

    Usage:
        def test_leds(configured_gpio):
            # Pins 12, 16, 20 already set up as outputs
            configured_gpio.write(12, PinState.HIGH)
    """
    # Setup common LED pins
    mock_gpio.setup_output(12)  # Green
    mock_gpio.setup_output(16)  # Orange
    mock_gpio.setup_output(20)  # Red

    return mock_gpio


# =============================================================================
# TTS FIXTURES
# =============================================================================

@pytest.fixture
def mock_tts_fast():
    """
    Provide MockTTS without timing simulation (fast tests).

    Use this for unit tests where you don't care about timing.

    Usage:
        def test_audio(mock_tts_fast):
            mock_tts_fast.speak("Hello")  # Returns instantly
    """
    tts = MockTTS(simulate_timing=False)
    yield tts
    tts.cleanup()


@pytest.fixture
def mock_tts_realistic():
    """
    Provide MockTTS with timing simulation (realistic tests).

    Use this for integration tests where timing matters.

    Usage:
        def test_queue_timing(mock_tts_realistic):
            mock_tts_realistic.speak("Hello")  # Takes realistic time
    """
    tts = MockTTS(simulate_timing=True)
    yield tts
    tts.cleanup()


# =============================================================================
# CONTROLLER FIXTURES
# =============================================================================

@pytest.fixture
def led_controller(mock_gpio):
    """
    Provide LEDController with mock GPIO.

    Automatically cleans up after test.

    Usage:
        def test_led(led_controller):
            led_controller.set_status(LEDPattern.READY)
    """
    from hardware.controllers.led_controller import LEDController

    controller = LEDController(gpio=mock_gpio)
    yield controller
    controller.cleanup()


@pytest.fixture
def button_controller(mock_gpio):
    """
    Provide ButtonController with mock GPIO.

    Usage:
        def test_button(button_controller, mock_gpio):
            # Simulate button press
            mock_gpio.simulate_button_press(18)
    """
    from hardware.controllers.button_controller import ButtonController

    controller = ButtonController(gpio=mock_gpio)
    yield controller
    controller.cleanup()


@pytest.fixture
def audio_controller(mock_tts_fast):
    """
    Provide AudioController with fast mock TTS.

    Usage:
        def test_audio(audio_controller):
            audio_controller.play_text("Hello")
    """
    from hardware.controllers.audio_controller import AudioController

    controller = AudioController(tts_engine=mock_tts_fast)
    yield controller
    controller.cleanup()


# =============================================================================
# HELPER FIXTURES
# =============================================================================

@pytest.fixture
def callback_tracker():
    """
    Provide a helper for tracking callback calls.

    Useful for testing async callbacks (button presses, etc).

    Usage:
        def test_callback(button_controller, callback_tracker):
            button_controller.register_callback(callback_tracker.track)
            # ... trigger callback ...
            assert callback_tracker.was_called()
            assert callback_tracker.get_call_count() == 1
    """
    class CallbackTracker:
        def __init__(self):
            self.calls = []

        def track(self, *args, **kwargs):
            """Record a callback invocation"""
            self.calls.append({'args': args, 'kwargs': kwargs})

        def was_called(self) -> bool:
            """Check if callback was called"""
            return len(self.calls) > 0

        def get_call_count(self) -> int:
            """Get number of times callback was called"""
            return len(self.calls)

        def get_last_call(self):
            """Get arguments from last call"""
            return self.calls[-1] if self.calls else None

        def reset(self):
            """Clear call history"""
            self.calls.clear()

    return CallbackTracker()


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """
    Configure pytest with custom markers.

    Markers let you categorize and selectively run tests:
        pytest -m unit          # Only unit tests
        pytest -m integration   # Only integration tests
        pytest -m "not slow"    # Skip slow tests
    """
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (may be slower)")
    config.addinivalue_line("markers", "slow: Slow tests (use sparingly)")
    config.addinivalue_line("markers", "hardware: Tests requiring real hardware")
