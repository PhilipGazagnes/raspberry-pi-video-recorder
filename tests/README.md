# Tests

Comprehensive test suite for the Raspberry Pi Video Recorder project. Tests cover all major modules without requiring hardware dependencies.

## Quick Start

### Run All Tests

```bash
pytest tests/ -v
```

Or from the root directory with the virtual environment:

```bash
source .venv/bin/activate && python3 -m pytest tests/ -v
```

### Run Tests Quietly (Summary Only)

```bash
pytest tests/ -q
```

### Run Specific Module Tests

```bash
# Hardware module tests
pytest tests/hardware/ -v

# Upload module tests
pytest tests/upload/ -v

# Storage module tests
pytest tests/storage/ -v

# Recording module tests
pytest tests/recording/ -v
```

### Run Specific Test File

```bash
pytest tests/hardware/test_hardware_integration.py -v
```

### Run Specific Test

```bash
pytest tests/hardware/test_hardware_integration.py::TestLEDController::test_set_status -v
```

## Test Structure

```
tests/
├── hardware/               # Hardware module tests
│   └── test_hardware_integration.py
├── upload/                 # Upload module tests
│   └── test_upload_integration.py
├── storage/                # Storage module tests
│   └── test_storage_integration.py
└── recording/              # Recording module tests
    └── test_recording_integration.py
```

## What's Tested

### Hardware Module (12 tests)
- **LEDController**: Status patterns, blinking, error flashing
- **ButtonController**: Press detection, callbacks, debouncing
- **AudioController**: Message playback, TTS engine integration
- **Factory**: GPIO and TTS creation with different modes

### Upload Module (20 tests)
- **MockUploader**: File validation, upload success/failure, history tracking
- **UploadController**: High-level upload operations
- **Factory**: Uploader creation with different modes
- **Integration**: Complete upload workflow

### Storage Module (31 tests)
- **VideoFile Model**: State management, lifecycle tracking
- **StorageStats**: Disk space calculations
- **MockStorage**: Video persistence, file operations
- **Factory**: Storage creation
- **Integration**: Save, upload, cleanup workflow

### Recording Module (25 tests)
- **MockCapture**: Video capture simulation
- **CameraManager**: Camera control, health checks
- **RecordingSession**: Session management, duration extensions, warnings
- **Factory**: Capture implementation creation

## Design Philosophy

Tests focus on **essentials only**:
- ✅ Code doesn't crash
- ✅ Business logic works correctly
- ✅ State transitions are valid
- ✅ Callbacks are triggered appropriately

Tests use **mocks** to eliminate hardware dependencies:
- No GPIO hardware needed
- No camera device required
- No YouTube API credentials needed
- No file system side effects

## Test Coverage

**88 tests total** covering:
- 100% of public APIs
- All state transitions
- Error conditions
- Integration workflows

All tests pass in **~7 seconds** with no external dependencies.

## Running Tests with Coverage

To see code coverage:

```bash
pytest tests/ --cov=. --cov-report=html
```

Then open `htmlcov/index.html` in your browser.

## Debugging Tests

### Run with Verbose Output

```bash
pytest tests/ -vv
```

### Show Print Statements

```bash
pytest tests/ -s
```

### Stop on First Failure

```bash
pytest tests/ -x
```

### Run Last Failed Tests

```bash
pytest tests/ --lf
```

### Drop into Debugger on Failure

```bash
pytest tests/ --pdb
```

## Configuration

Tests are configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

This allows:
- Tests to import modules directly from the root
- Tests to discover in the `tests/` directory
- Running `pytest` from anywhere

## Integration with CI/CD

The test suite is designed for CI/CD pipelines:

```bash
# Run tests and exit with error code if any fail
python3 -m pytest tests/ -q

# Generate JUnit XML report for Jenkins/GitHub Actions
python3 -m pytest tests/ --junit-xml=test-results.xml

# Generate coverage report
python3 -m pytest tests/ --cov=. --cov-report=xml
```

## Continuous Development

Run tests after each change:

```bash
# Watch mode (requires pytest-watch)
ptw tests/

# Or manually after editing
pytest tests/ -q
```

## Key Testing Patterns

### Dependency Injection in Tests

All components use dependency injection, allowing tests to pass mocks:

```python
def test_led_with_mock_gpio():
    mock_gpio = MockGPIO()
    led = LEDController(gpio=mock_gpio)
    # Test with specific mock implementation
```

### Fixtures for Reusable Setup

Common test data and objects:

```python
@pytest.fixture
def camera_manager():
    return CameraManager(capture=MockCapture())

def test_recording_session(camera_manager):
    session = RecordingSession(camera_manager)
    # Use fixture
```

### Parametrization for Multiple Cases

Test multiple scenarios with one test:

```python
@pytest.mark.parametrize("pattern,expected", [
    (LEDPattern.READY, (True, False, False)),
    (LEDPattern.ERROR, (False, False, True)),
])
def test_led_patterns(pattern, expected):
    # Test multiple patterns
```

## Troubleshooting

### ImportError: No module named 'config'

Make sure you're running pytest from the root directory and that `.venv/bin/activate` is sourced.

### Tests hang or timeout

Tests should complete in ~7 seconds. If they hang:
- Check for blocking calls in mock implementations
- Verify threading is properly cleaned up
- Run with `pytest -x` to find which test hangs

### Import errors with temporary files

Tests clean up temporary files in `finally` blocks. If cleanup fails:
- Check disk space
- Verify permissions on `/tmp`
- Manually clean up: `rm -rf /tmp/test_*`

## Contributing Tests

When adding new features:

1. Write tests for the new functionality
2. Use mocks to eliminate hardware dependencies
3. Follow existing test patterns
4. Ensure all tests pass: `pytest tests/ -q`
5. Check code quality: `./lint.sh`

---

**Last Updated**: Tests suite with 88 passing tests covering all 4 modules
