# Recording Module Testing Guide

## Overview

Comprehensive test suite for the recording module with ~100 tests covering:
- Video capture (mock and FFmpeg)
- Camera lifecycle management
- Recording sessions with duration tracking
- Utility functions

## Test Structure

```
tests/recording/
├── conftest.py                              # Shared fixtures
├── implementations/
│   ├── test_mock_capture.py                # MockCapture tests (25 tests)
│   └── test_ffmpeg_capture.py              # FFmpeg unit tests (planned)
├── controllers/
│   ├── test_camera_manager.py              # CameraManager tests (20 tests)
│   └── test_recording_session.py           # RecordingSession tests (35 tests)
└── utils/
    └── test_recording_utils.py             # Utility tests (20 tests)
```

## Running Tests

### Run all recording tests
```bash
pytest tests/recording/ -v
```

### Run specific test file
```bash
pytest tests/recording/controllers/test_camera_manager.py -v
```

### Run by marker
```bash
# Fast unit tests only
pytest tests/recording/ -m unit -v

# Integration tests
pytest tests/recording/ -m unit_integration -v

# Skip slow tests
pytest tests/recording/ -m "not slow" -v
```

## Key Test Patterns

### 1. Using Fixtures
```python
def test_camera_start(camera_manager, temp_video_file):
    # camera_manager and temp_video_file auto-configured
    camera_manager.start_recording(temp_video_file)
```

### 2. Testing Async Behavior
```python
def test_auto_stop():
    session.start(file, duration=0.5)
    time.sleep(0.7)  # Wait for auto-stop
    assert session.state == RecordingState.IDLE
```

### 3. Testing Callbacks
```python
def test_callback(recording_session, callback_tracker):
    recording_session.on_warning = callback_tracker.track
    # ... trigger warning ...
    assert callback_tracker.was_called()
```

### 4. Testing With Realistic Timing
```python
def test_duration(camera_manager_realistic, temp_video_file):
    camera_manager_realistic.start_recording(temp_video_file)
    time.sleep(0.3)
    duration = camera_manager_realistic.get_recording_duration()
    assert 0.2 < duration < 0.4  # Around 0.3 seconds
```

## Fixtures Reference

### Capture Fixtures
- `mock_capture_fast` - Mock capture without timing (instant)
- `mock_capture_realistic` - Mock capture with real timing simulation

### Manager Fixtures
- `camera_manager` - CameraManager with fast mock
- `camera_manager_realistic` - CameraManager with realistic timing
- `recording_session` - RecordingSession ready to use

### File Fixtures
- `temp_video_file` - Single temp video file path (auto-cleanup)
- `temp_recording_dir` - Temp directory for multiple files (auto-cleanup)

### Helper Fixtures
- `callback_tracker` - Track callback invocations

## Mock Capture Helpers

### Test Configuration
```python
mock.simulate_start_failure()  # Next start will fail
mock.simulate_crash_during_capture(after_seconds=2.0)  # Crash after 2s
mock.reset_test_config()  # Reset to normal
```

### Verification
```python
frames = mock.get_simulated_frames()  # Get frame count
health = mock.check_health()  # Check capture health
```

## Common Test Scenarios

### Test Recording Lifecycle
```python
def test_lifecycle(camera_manager, temp_video_file):
    # Start
    assert camera_manager.start_recording(temp_video_file) is True
    assert camera_manager.is_recording() is True

    # Stop
    assert camera_manager.stop_recording() is True
    assert camera_manager.is_recording() is False
```

### Test Duration Limits
```python
def test_max_duration(recording_session, temp_video_file):
    # Should accept max duration
    success = recording_session.start(temp_video_file, MAX_RECORDING_DURATION)
    assert success is True

    # Should reject over max
    success = recording_session.start(temp_video_file, MAX_RECORDING_DURATION + 1)
    assert success is False
```

### Test Extensions
```python
def test_extension(recording_session, temp_video_file):
    recording_session.start(temp_video_file, DEFAULT_RECORDING_DURATION)

    initial = recording_session.get_duration_limit()
    recording_session.extend()
    new = recording_session.get_duration_limit()

    assert new == initial + EXTENSION_DURATION
```

### Test Auto-Stop
```python
def test_auto_stop(camera_manager_realistic):
    temp_file = Path("/tmp/test.mp4")
    session = RecordingSession(camera_manager_realistic)

    session.start(temp_file, duration=0.5)
    time.sleep(0.7)

    assert session.state == RecordingState.IDLE
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- Fast, isolated tests
- Use mocks exclusively
- Test single components
- No real file I/O or FFmpeg

### Unit Integration Tests (`@pytest.mark.unit_integration`)
- Test component interactions
- May use realistic timing
- Test complete workflows
- Still use mocks (no real hardware)

### Slow Tests (`@pytest.mark.slow`)
- Tests that take > 1 second
- Comprehensive scenarios
- Optional in quick test runs

## Coverage

Run with coverage report:
```bash
pytest tests/recording/ --cov=recording --cov-report=html
```

View coverage:
```bash
open htmlcov/index.html
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Test Recording Module

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
      - run: pytest tests/recording/ -v --cov=recording
```

## Writing New Tests

1. **Choose appropriate fixture**
   - Use `*_fast` for unit tests
   - Use `*_realistic` for timing-dependent tests

2. **Add proper markers**
   ```python
   @pytest.mark.unit
   @pytest.mark.unit_integration
   ```

3. **Use descriptive names**
   ```python
   def test_recording_session_cannot_extend_beyond_max()
   ```

4. **Clean up resources**
   - Fixtures handle most cleanup
   - Explicitly cleanup in integration tests if needed

## Troubleshooting

### Tests timeout
- Increase timeout in `wait_until_idle(timeout=10.0)`
- Use `mock_capture_fast` instead of `realistic`

### Intermittent failures
- Add `time.sleep()` buffers for thread synchronization
- Use longer timeouts

### File cleanup issues
- Fixtures auto-cleanup temp files
- Check for unclosed file handles

## Summary

- ✅ ~100 comprehensive tests
- ✅ Mock-based (no FFmpeg required)
- ✅ Fast unit tests + realistic integration tests
- ✅ Callback and async testing
- ✅ Complete workflow coverage
- ✅ CI/CD ready

Run `pytest tests/recording/ -v` to see all tests!
