# Hardware Module Testing Guide

## Overview

This guide explains the comprehensive test suite for the refactored hardware module. The tests demonstrate proper testing patterns for hardware controllers, async behavior, and mocked dependencies.

## Test Structure

```
tests/
└── hardware/
    ├── conftest.py                           # Shared fixtures
    ├── controllers/
    │   ├── __init__.py
    │   ├── test_led_controller.py           # LED tests (15 tests)
    │   ├── test_button_controller.py        # Button tests (15 tests)
    │   └── test_audio_controller.py         # Audio tests (20 tests)
    └── audio/
        ├── __init__.py
        ├── test_message_library.py          # Message library tests (15 tests)
        └── test_audio_queue.py              # Audio queue tests (15 tests)

Total: ~80 comprehensive tests
```

## Running Tests

### Install pytest

```bash
# Install pytest (if not already installed)
pip install pytest

# Or with your virtual environment
.venv/bin/pip install pytest
```

### Run all tests

```bash
# Run all hardware tests with verbose output
pytest tests/hardware/ -v

# Run with detailed output and show print statements
pytest tests/hardware/ -v -s

# Run with coverage report
pytest tests/hardware/ --cov=hardware --cov-report=html
```

### Run specific test files

```bash
# Test LED controller only
pytest tests/hardware/controllers/test_led_controller.py -v

# Test button controller only
pytest tests/hardware/controllers/test_button_controller.py -v

# Test audio system
pytest tests/hardware/audio/ -v
```

### Run specific test functions

```bash
# Run single test
pytest tests/hardware/controllers/test_led_controller.py::test_led_initialization -v

# Run tests matching pattern
pytest tests/hardware/ -k "single_press" -v
```

### Run by marker

```bash
# Run only unit tests (fast)
pytest tests/hardware/ -m unit -v

# Run only integration tests
pytest tests/hardware/ -m integration -v

# Skip slow tests
pytest tests/hardware/ -m "not slow" -v
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- Fast, isolated tests
- Test single components
- Use mocks exclusively
- Run in < 1 second

### Unit Integration Tests (`@pytest.mark.unit_integration`)
- Test component interactions
- May use realistic timing
- Test complete workflows
- Run in 1-5 seconds

### Slow Tests (`@pytest.mark.slow`)
- Comprehensive tests
- Test all messages/patterns
- May take > 5 seconds
- Optional in quick test runs

## Fixtures Explained

### GPIO Fixtures

**`mock_gpio`** - Fresh MockGPIO instance
```python
def test_something(mock_gpio):
    # Use mock GPIO
    mock_gpio.setup_output(12)
```

**`configured_gpio`** - Pre-configured with LED pins
```python
def test_leds(configured_gpio):
    # Pins 12, 16, 20 already set up
    configured_gpio.write(12, PinState.HIGH)
```

### TTS Fixtures

**`mock_tts_fast`** - Instant speech (no timing simulation)
```python
def test_audio(mock_tts_fast):
    # Fast tests - speech returns instantly
    mock_tts_fast.speak("Hello")
```

**`mock_tts_realistic`** - Realistic speech timing
```python
def test_timing(mock_tts_realistic):
    # Simulates real speech duration
    mock_tts_realistic.speak("Hello")  # Takes ~1 second
```

### Controller Fixtures

**`led_controller`** - Ready-to-use LED controller
```python
def test_led(led_controller):
    led_controller.set_status(LEDPattern.READY)
```

**`button_controller`** - Ready-to-use button controller
```python
def test_button(button_controller):
    # Controller ready with mock GPIO
```

**`audio_controller`** - Ready-to-use audio controller
```python
def test_audio(audio_controller):
    audio_controller.play_text("Hello")
```

### Helper Fixtures

**`callback_tracker`** - Track callback invocations
```python
def test_callback(button_controller, callback_tracker):
    button_controller.register_callback(callback_tracker.track)
    # ... trigger callback ...
    assert callback_tracker.was_called()
    assert callback_tracker.get_call_count() == 1
```

## Testing Patterns Demonstrated

### 1. Testing Hardware with Mocks

```python
@pytest.mark.unit
def test_led_ready_pattern(led_controller, mock_gpio):
    # Set LED pattern
    led_controller.set_status(LEDPattern.READY)

    # Verify hardware state with mock
    assert mock_gpio.get_pin_state(12) == PinState.HIGH
    assert mock_gpio.get_pin_state(16) == PinState.LOW
```

**Why this works:**
- MockGPIO tracks all pin states
- Can verify exact hardware behavior
- No real GPIO needed for testing

### 2. Testing Async/Threaded Behavior

```python
@pytest.mark.unit
def test_led_recording_pattern_starts_blinking(led_controller, mock_gpio):
    # Start blinking
    led_controller.set_status(LEDPattern.RECORDING)

    # Give thread time to start
    time.sleep(0.1)

    # Verify blinking by checking state changes
    initial_state = mock_gpio.get_pin_state(12)
    time.sleep(0.6)
    current_state = mock_gpio.get_pin_state(12)

    assert current_state != initial_state
```

**Why this works:**
- Use `time.sleep()` to wait for threads
- Check state changes over time
- Verifies async behavior without complex mocking

### 3. Testing Callbacks

```python
@pytest.mark.unit
def test_button_single_press(button_controller, mock_gpio, callback_tracker):
    # Register tracker
    button_controller.register_callback(callback_tracker.track)

    # Simulate button press
    mock_gpio.simulate_button_press(18)
    time.sleep(0.6)  # Wait for processing

    # Verify callback was called
    assert callback_tracker.was_called()
    last_call = callback_tracker.get_last_call()
    assert last_call['args'][0] == ButtonPress.SINGLE
```

**Why this works:**
- `callback_tracker` records all callback invocations
- Can verify callback was called and with what arguments
- No complex mocking needed

### 4. Testing Error Handling

```python
@pytest.mark.unit
def test_button_callback_exception_handling(button_controller, mock_gpio, caplog):
    def bad_callback(press_type):
        raise ValueError("Intentional error")

    button_controller.register_callback(bad_callback)
    mock_gpio.simulate_button_press(18)
    time.sleep(0.6)

    # Should log error but not crash
    assert "error in button callback" in caplog.text.lower()
```

**Why this works:**
- `caplog` fixture captures log messages
- Verifies system handles errors gracefully
- Tests robustness

### 5. Testing Queue/Sequential Behavior

```python
@pytest.mark.unit
def test_audio_queue_play_multiple_messages(mock_tts_fast):
    queue = AudioQueue(mock_tts_fast)

    # Queue messages
    queue.play("Message 1")
    queue.play("Message 2")
    queue.play("Message 3")

    # Wait for all
    queue.wait_until_idle()

    # Verify order
    history = mock_tts_fast.get_speech_history()
    assert history == ["Message 1", "Message 2", "Message 3"]
```

**Why this works:**
- MockTTS tracks speech history
- Can verify order and content
- Tests sequential processing

### 6. Integration Testing

```python
@pytest.mark.unit_integration
def test_audio_complete_workflow(mock_tts_fast):
    audio = AudioController(tts_engine=mock_tts_fast)

    # Simulate real usage
    audio.play_message(AudioMessage.SYSTEM_READY)
    audio.wait_until_idle()

    audio.play_message(AudioMessage.RECORDING_START)
    audio.wait_until_idle()

    # Verify complete flow worked
    history = mock_tts_fast.get_speech_history()
    assert len(history) == 2
```

**Why this works:**
- Tests multiple components together
- Simulates real-world usage
- Catches integration issues

## Best Practices Demonstrated

### ✅ Use Fixtures for Reusable Setup
Instead of:
```python
def test_something():
    gpio = MockGPIO()
    led = LEDController(gpio=gpio)
    # ... test ...
    led.cleanup()
```

Use fixtures:
```python
def test_something(led_controller):
    # Already set up, auto-cleanup
    # ... test ...
```

### ✅ Test One Thing Per Test
Each test should verify one specific behavior:
```python
# Good - tests one thing
def test_led_ready_pattern(led_controller, mock_gpio):
    led_controller.set_status(LEDPattern.READY)
    assert mock_gpio.get_pin_state(12) == PinState.HIGH

# Bad - tests multiple things
def test_led_all_patterns(led_controller, mock_gpio):
    # Tests 5 different things - hard to debug if fails
```

### ✅ Use Descriptive Test Names
Test names should describe what they test:
```python
# Good
def test_button_double_press_timing_window()

# Bad
def test_button_2()
```

### ✅ Arrange-Act-Assert Pattern
Structure tests clearly:
```python
def test_something():
    # Arrange - set up
    led = LEDController()

    # Act - do the thing
    led.set_status(LEDPattern.READY)

    # Assert - verify result
    assert led.current_pattern == LEDPattern.READY
```

### ✅ Test Error Conditions
Don't just test happy path:
```python
def test_button_invalid_timing_values(button_controller):
    # Test that invalid input is rejected
    with pytest.raises(ValueError):
        button_controller.set_timing(debounce_time=0.001)
```

### ✅ Use Markers to Categorize Tests
```python
@pytest.mark.unit               # Fast unit test
@pytest.mark.unit_integration   # Unit Integration test
@pytest.mark.slow               # Slow test (skip in quick runs)
@pytest.mark.hardware           # Requires real hardware
```

## Mock Helper Methods

### MockGPIO
- `simulate_button_press(pin)` - Simulate single press
- `simulate_double_press(pin, delay_ms)` - Simulate double press
- `get_pin_state(pin)` - Get current pin state
- `get_pin_info(pin)` - Get pin configuration

### MockTTS
- `was_spoken(text)` - Check if text was spoken
- `get_speech_history()` - Get all spoken text
- `get_last_speech()` - Get most recent speech
- `clear_history()` - Reset history
- `get_config()` - Get TTS configuration

### CallbackTracker
- `track(*args, **kwargs)` - Callback function to register
- `was_called()` - Check if callback was called
- `get_call_count()` - Get number of calls
- `get_last_call()` - Get last call arguments
- `reset()` - Clear call history

## Continuous Integration

### GitHub Actions Example

```yaml
name: Test Hardware Module

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/hardware/ -v --cov=hardware
```

## Common Issues and Solutions

### Issue: Tests timeout or hang
**Cause:** Waiting for thread/queue that never completes
**Solution:** Always use timeouts in `wait_until_idle(timeout=5.0)`

### Issue: Intermittent test failures
**Cause:** Race conditions in threaded code
**Solution:** Add small `time.sleep()` buffers after starting threads

### Issue: Tests fail on CI but pass locally
**Cause:** Timing differences between systems
**Solution:** Use longer timeouts in CI, or use `mock_tts_fast` (no timing)

### Issue: Can't verify callback was called
**Cause:** Not waiting long enough for async processing
**Solution:** Add `time.sleep()` after triggering callback

## Writing New Tests

When adding new tests:

1. **Choose the right fixture**
   - Use `mock_tts_fast` for unit tests (fast)
   - Use `mock_tts_realistic` for integration tests (realistic)

2. **Add appropriate markers**
   ```python
   @pytest.mark.unit
   @pytest.mark.unit_integration
   @pytest.mark.slow
   ```

3. **Follow naming convention**
   - `test_<component>_<behavior>`
   - Example: `test_led_ready_pattern`

4. **Add docstring**
   ```python
   def test_something():
       """
       Test that something does what it should.

       Scenario:
       1. Set up condition
       2. Perform action
       3. Verify result
       """
   ```

5. **Keep tests isolated**
   - Each test should work independently
   - Don't depend on test execution order
   - Use fixtures for setup/cleanup

## Summary

The test suite demonstrates:
- ✅ 80+ comprehensive tests
- ✅ Unit and integration testing
- ✅ Mock hardware for testing
- ✅ Async/threaded code testing
- ✅ Error handling verification
- ✅ Complete workflow testing
- ✅ Best practices and patterns
- ✅ CI/CD ready

Run `pytest tests/hardware/ -v` to see all tests pass!
