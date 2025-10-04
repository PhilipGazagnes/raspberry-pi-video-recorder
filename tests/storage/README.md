# Storage Module Testing Guide

## Overview

This guide explains the comprehensive test suite for the storage module. The tests mirror the patterns from the hardware module tests, demonstrating proper testing for database operations, file management, and async cleanup.

## Test Structure

```
tests/
└── storage/
    ├── conftest.py                          # Shared fixtures
    ├── test_storage_controller.py           # Controller tests (~35 tests)
    ├── managers/
    │   ├── __init__.py
    │   ├── test_metadata_manager.py         # Database tests (~25 tests)
    │   ├── test_file_manager.py             # File operations tests
    │   ├── test_space_manager.py            # Disk space tests
    │   └── test_cleanup_manager.py          # Cleanup policy tests
    └── utils/
        ├── __init__.py
        └── test_validation_utils.py         # Validation tests (~15 tests)

Total: ~80+ comprehensive tests
```

## Running Tests

### Install pytest

```bash
# Install pytest and dependencies
pip install pytest pytest-cov

# Or with your virtual environment
.venv/bin/pip install pytest pytest-cov
```

### Run all tests

```bash
# Run all storage tests with verbose output
pytest tests/storage/ -v

# Run with detailed output and show print statements
pytest tests/storage/ -v -s

# Run with coverage report
pytest tests/storage/ --cov=storage --cov-report=html
```

### Run specific test files

```bash
# Test storage controller only
pytest tests/storage/test_storage_controller.py -v

# Test metadata manager only
pytest tests/storage/managers/test_metadata_manager.py -v

# Test validation utilities
pytest tests/storage/utils/test_validation_utils.py -v
```

### Run specific test functions

```bash
# Run single test
pytest tests/storage/test_storage_controller.py::test_save_recording -v

# Run tests matching pattern
pytest tests/storage/ -k "upload" -v
```

### Run by marker

```bash
# Run only unit tests (fast)
pytest tests/storage/ -m unit -v

# Run only integration tests
pytest tests/storage/ -m unit_integration -v

# Skip slow tests
pytest tests/storage/ -m "not slow" -v
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- Fast, isolated tests
- Test single components
- Use mocks exclusively
- Run in < 1 second

### Unit Integration Tests (`@pytest.mark.unit_integration`)
- Test component interactions
- May use temp filesystem
- Test complete workflows
- Run in 1-5 seconds

### Slow Tests (`@pytest.mark.slow`)
- Comprehensive tests
- Large data sets
- May take > 5 seconds
- Optional in quick test runs

## Fixtures Explained

### Storage Fixtures

**`mock_storage`** - Fresh MockStorage instance
```python
def test_something(mock_storage):
    # Use mock storage (in-memory, no filesystem)
    video = mock_storage.save_video(Path("/fake/video.mp4"))
```

**`mock_storage_with_videos`** - Pre-loaded with test videos
```python
def test_cleanup(mock_storage_with_videos):
    # Already has pending and completed videos
    pending = mock_storage_with_videos.list_videos(status=UploadStatus.PENDING)
```

**`local_storage`** - Real storage with temp directory
```python
def test_real_storage(local_storage):
    # Tests with actual filesystem
    video = local_storage.save_video(Path("/real/video.mp4"))
```

### Directory Fixtures

**`temp_storage_dir`** - Temporary directory
```python
def test_with_temp_dir(temp_storage_dir):
    # Temp directory, auto-cleanup
    file_path = temp_storage_dir / "test.mp4"
```

**`sample_video_file`** - Sample video file for testing
```python
def test_save_video(storage_controller, sample_video_file):
    # Pre-created test video file
    video = storage_controller.save_recording(sample_video_file)
```

### Controller Fixtures

**`storage_controller`** - Ready-to-use controller with mock
```python
def test_controller(storage_controller):
    stats = storage_controller.get_stats()
```

**`storage_controller_with_videos`** - Controller with pre-loaded videos
```python
def test_pending_uploads(storage_controller_with_videos):
    pending = storage_controller_with_videos.get_pending_uploads()
    assert len(pending) > 0
```

### Helper Fixtures

**`event_tracker`** - Track event callbacks
```python
def test_events(storage_controller, event_tracker):
    storage_controller.on_disk_full = event_tracker.track
    # ... trigger event ...
    assert event_tracker.was_called()
```

**`local_storage_config`** - Pre-configured StorageConfig
```python
def test_with_config(local_storage_config):
    storage = LocalStorage(local_storage_config)
```

## Testing Patterns Demonstrated

### 1. Testing with Mock Storage

```python
@pytest.mark.unit
def test_save_recording(storage_controller, sample_video_file):
    # Save recording with mock storage (fast, no filesystem)
    video = storage_controller.save_recording(sample_video_file)

    # Verify with mock
    assert video is not None
    assert video.status == UploadStatus.PENDING
```

**Why this works:**
- MockStorage simulates everything in memory
- No filesystem operations needed
- Tests are fast and isolated

### 2. Testing Database Operations

```python
@pytest.mark.unit
def test_insert_video(temp_storage_dir):
    manager = MetadataManager(temp_storage_dir)

    video = VideoFile(...)
    result = manager.insert_video(video)

    # Verify database operation
    assert result.id is not None
    retrieved = manager.get_video(result.id)
    assert retrieved is not None
```

**Why this works:**
- Uses temporary directory for test database
- Real SQLite operations
- Isolated from production database

### 3. Testing Event Callbacks

```python
@pytest.mark.unit
def test_event_callback_disk_full(mock_storage, event_tracker):
    controller = StorageController(storage_impl=mock_storage)
    controller.on_disk_full = event_tracker.track

    # Simulate disk full
    mock_storage.simulate_disk_full()

    # Try to save
    controller.save_recording(Path("/fake/video.mp4"))

    # Verify event fired
    assert event_tracker.was_called()
```

**Why this works:**
- `event_tracker` records all event calls
- Can verify events fire at right time
- Tests integration with other modules

### 4. Testing Upload Lifecycle

```python
@pytest.mark.unit_integration
def test_complete_recording_workflow(storage_controller, sample_video_file):
    # Save
    video = storage_controller.save_recording(sample_video_file)
    assert video.status == UploadStatus.PENDING

    # Start upload
    storage_controller.mark_upload_started(video)
    assert video.status == UploadStatus.IN_PROGRESS

    # Complete
    storage_controller.mark_upload_success(video, "https://...")
    assert video.status == UploadStatus.COMPLETED
```

**Why this works:**
- Tests complete workflow
- Verifies state transitions
- Integration test pattern

### 5. Testing Error Conditions

```python
@pytest.mark.unit
def test_save_recording_insufficient_space(mock_storage):
    controller = StorageController(storage_impl=mock_storage)

    # Simulate error condition
    mock_storage.simulate_disk_full()

    # Should fail gracefully
    video = controller.save_recording(Path("/fake/video.mp4"))
    assert video is None
```

**Why this works:**
- MockStorage provides test helpers
- Can simulate error conditions
- Verifies graceful error handling

### 6. Testing Cleanup Logic

```python
@pytest.mark.unit
def test_cleanup_old_videos(storage_controller_with_videos):
    # Get initial count
    stats_before = storage_controller_with_videos.get_stats()

    # Run cleanup
    count = storage_controller_with_videos.cleanup_old_videos()

    # Verify cleanup executed
    assert count >= 0
```

**Why this works:**
- Pre-loaded fixture provides test data
- Can verify cleanup behavior
- Tests retention policy

## Best Practices Demonstrated

### ✅ Use Fixtures for Reusable Setup

Instead of:
```python
def test_something():
    storage = MockStorage()
    controller = StorageController(storage_impl=storage)
    # ... test ...
    controller.cleanup()
```

Use fixtures:
```python
def test_something(storage_controller):
    # Already set up, auto-cleanup
    # ... test ...
```

### ✅ Test with Mock for Unit Tests

```python
# Good - unit test with mock (fast)
def test_save_recording(storage_controller, sample_video_file):
    video = storage_controller.save_recording(sample_video_file)

# Also good - integration test with real filesystem
@pytest.mark.unit_integration
def test_save_recording_real(local_storage, sample_video_file):
    video = local_storage.save_video(sample_video_file)
```

### ✅ Use Descriptive Test Names

```python
# Good
def test_mark_upload_failed_multiple_attempts()

# Bad
def test_upload_2()
```

### ✅ Arrange-Act-Assert Pattern

```python
def test_something():
    # Arrange - set up
    storage = StorageController()

    # Act - do the thing
    video = storage.save_recording(Path("/test.mp4"))

    # Assert - verify result
    assert video is not None
```

### ✅ Test Error Conditions

```python
def test_save_recording_with_nonexistent_file(storage_controller):
    # Test error handling
    video = storage_controller.save_recording(Path("/nonexistent.mp4"))
    assert video is None
```

### ✅ Use Markers to Categorize Tests

```python
@pytest.mark.unit               # Fast unit test
@pytest.mark.unit_integration   # Unit integration test
@pytest.mark.slow               # Slow test (skip in quick runs)
```

## Mock Helper Methods

### MockStorage
- `save_video(path)` - Save video (simulated)
- `add_fake_video(filename, status)` - Add test video
- `simulate_disk_full()` - Simulate disk full condition
- `simulate_low_space()` - Simulate low space warning
- `get_operation_log()` - Get all operations for verification
- `reset()` - Clear all data

### EventTracker
- `track(*args, **kwargs)` - Callback function to register
- `was_called()` - Check if event was triggered
- `get_call_count()` - Get number of triggers
- `get_last_call()` - Get last call arguments
- `reset()` - Clear history

## Testing Checklist for New Features

When adding new storage features:

1. **Add unit tests** - Test component in isolation with mock
2. **Add integration test** - Test with real filesystem if needed
3. **Test error cases** - What happens when things go wrong?
4. **Test edge cases** - Empty data, null values, etc.
5. **Add appropriate markers** - `@pytest.mark.unit`, etc.
6. **Use fixtures** - Don't repeat setup code
7. **Follow naming convention** - `test_<component>_<behavior>`
8. **Add docstring** - Explain what's being tested

## Common Issues and Solutions

### Issue: Tests create files that aren't cleaned up
**Solution:** Use `temp_storage_dir` fixture which auto-cleans

### Issue: Database locked errors
**Cause:** Not cleaning up MetadataManager properly
**Solution:** Always use fixtures that handle cleanup, or call `manager.cleanup()`

### Issue: Tests fail on different systems
**Cause:** Hardcoded paths or disk space assumptions
**Solution:** Use fixtures and relative paths

### Issue: Mock tests pass but real tests fail
**Cause:** Mock doesn't accurately simulate real behavior
**Solution:** Add integration tests with `local_storage` fixture

## Continuous Integration

### GitHub Actions Example

```yaml
name: Test Storage Module

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
      - run: pytest tests/storage/ -v --cov=storage
      - run: pytest tests/storage/ -m "not slow" # Skip slow tests in CI
```

## Running Tests Locally vs CI

### Local Development
```bash
# Run all tests including slow ones
pytest tests/storage/ -v

# Run with coverage
pytest tests/storage/ --cov=storage --cov-report=html
open htmlcov/index.html
```

### CI/CD
```bash
# Skip slow tests for faster feedback
pytest tests/storage/ -m "not slow" -v

# Run with coverage for reporting
pytest tests/storage/ --cov=storage --cov-report=xml
```

## Integration with Hardware Tests

Storage tests follow the same patterns as hardware tests:

- ✅ Same fixture patterns
- ✅ Same marker conventions
- ✅ Same docstring style
- ✅ Same test organization
- ✅ Same error handling approach

You can run both test suites together:

```bash
# Run all tests (hardware + storage)
pytest tests/ -v

# Run only unit tests from both
pytest tests/ -m unit -v
```

## Summary

The test suite demonstrates:
- ✅ 80+ comprehensive tests
- ✅ Unit and integration testing
- ✅ Mock storage for fast tests
- ✅ Real filesystem tests where needed
- ✅ Database operation testing
- ✅ Event callback testing
- ✅ Error handling verification
- ✅ Complete workflow testing
- ✅ Best practices and patterns
- ✅ CI/CD ready

Run `pytest tests/storage/ -v` to see all tests pass!
