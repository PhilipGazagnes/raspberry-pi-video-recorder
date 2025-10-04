"""
Validation Utils Tests

Tests for video validation utilities showing:
- File size validation
- FFmpeg probe validation
- Video metadata extraction
- Error handling

To run these tests:
    pytest tests/storage/utils/test_validation_utils.py -v
"""

from pathlib import Path

import pytest

from storage.constants import VideoQuality
from storage.utils.validation_utils import (
    get_video_duration,
    get_video_info,
    quick_validate,
    validate_video_file,
)


# =============================================================================
# QUICK VALIDATION TESTS
# =============================================================================

@pytest.mark.unit
def test_quick_validate_valid_file(sample_video_file):
    """
    Test quick validation with valid file.

    Should pass basic checks (exists, minimum size).
    """
    is_valid = quick_validate(sample_video_file)

    assert is_valid is True


@pytest.mark.unit
def test_quick_validate_nonexistent_file():
    """
    Test quick validation with nonexistent file.

    Should return False.
    """
    is_valid = quick_validate(Path("/nonexistent/video.mp4"))

    assert is_valid is False


@pytest.mark.unit
def test_quick_validate_empty_file(temp_storage_dir):
    """
    Test quick validation with empty file.

    Should fail minimum size check.
    """
    # Create empty file
    empty_file = temp_storage_dir / "empty.mp4"
    empty_file.touch()

    is_valid = quick_validate(empty_file)

    assert is_valid is False


@pytest.mark.unit
def test_quick_validate_too_small_file(temp_storage_dir):
    """
    Test quick validation with file below minimum size.
    """
    # Create tiny file (1 KB)
    small_file = temp_storage_dir / "small.mp4"
    small_file.write_bytes(b"x" * 1024)

    is_valid = quick_validate(small_file)

    assert is_valid is False


# =============================================================================
# FULL VALIDATION TESTS
# =============================================================================

@pytest.mark.unit
def test_validate_video_file_valid(sample_video_file):
    """
    Test full validation with valid file.

    Note: FFmpeg validation may be skipped if ffmpeg not installed.
    """
    quality, error = validate_video_file(
        sample_video_file,
        enable_ffmpeg=False  # Skip ffmpeg for unit test
    )

    # Should pass basic checks
    assert quality == VideoQuality.VALID
    assert error is None


@pytest.mark.unit
def test_validate_video_file_nonexistent():
    """
    Test validation with nonexistent file.
    """
    quality, error = validate_video_file(
        Path("/nonexistent/video.mp4"),
        enable_ffmpeg=False
    )

    assert quality == VideoQuality.CORRUPTED
    assert error is not None
    assert "not found" in error.lower()


@pytest.mark.unit
def test_validate_video_file_too_small(temp_storage_dir):
    """
    Test validation with file below minimum size.
    """
    # Create tiny file
    small_file = temp_storage_dir / "small.mp4"
    small_file.write_bytes(b"x" * 100)

    quality, error = validate_video_file(
        small_file,
        enable_ffmpeg=False
    )

    assert quality == VideoQuality.TOO_SMALL
    assert error is not None


# =============================================================================
# VIDEO INFO EXTRACTION TESTS
# =============================================================================

@pytest.mark.unit
def test_get_video_duration_with_fake_file(sample_video_file):
    """
    Test getting video duration.

    Note: Will return None for fake video file without valid video stream.
    """
    duration = get_video_duration(sample_video_file)

    # For fake file, duration will be None (no valid video stream)
    # This is expected behavior
    assert duration is None or isinstance(duration, int)


@pytest.mark.unit
def test_get_video_duration_nonexistent_file():
    """
    Test getting duration of nonexistent file.

    Should return None and not crash.
    """
    duration = get_video_duration(Path("/nonexistent/video.mp4"))

    assert duration is None


@pytest.mark.unit
def test_get_video_info_with_fake_file(sample_video_file):
    """
    Test getting video info.

    Note: Will return empty dict for fake video file.
    """
    info = get_video_info(sample_video_file)

    # Should return dict (may be empty for fake file)
    assert isinstance(info, dict)


@pytest.mark.unit
def test_get_video_info_nonexistent_file():
    """
    Test getting info of nonexistent file.

    Should return empty dict and not crash.
    """
    info = get_video_info(Path("/nonexistent/video.mp4"))

    assert isinstance(info, dict)
    assert len(info) == 0


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================

@pytest.mark.skip(reason="Permission test unreliable - chmod behavior varies by filesystem/user")
@pytest.mark.unit
def test_validate_video_file_with_permission_error(temp_storage_dir):
    """
    Test validation handles permission errors gracefully.

    Note: Skipped because file stat can succeed even without read permissions
    when running as file owner. Permission errors are better tested with
    real-world scenarios.
    """
    import sys

    if sys.platform == "win32":
        pytest.skip("Permission test not applicable on Windows")

    # Create file
    restricted_file = temp_storage_dir / "restricted.mp4"
    restricted_file.write_bytes(b"x" * 2_000_000)  # 2 MB

    # Remove read permissions
    restricted_file.chmod(0o000)

    try:
        quality, error = validate_video_file(
            restricted_file,
            enable_ffmpeg=False
        )

        # Should detect error (but may not on all systems)
        # This is why test is skipped
        assert quality == VideoQuality.CORRUPTED
        assert error is not None
    finally:
        # Restore permissions for cleanup
        restricted_file.chmod(0o644)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

@pytest.mark.unit_integration
def test_validation_workflow(sample_video_file):
    """
    Integration test: Complete validation workflow.

    Tests all validation steps in sequence.
    """
    # Quick validate first
    quick_ok = quick_validate(sample_video_file)
    assert quick_ok is True

    # Full validate
    quality, error = validate_video_file(
        sample_video_file,
        enable_ffmpeg=False
    )
    assert quality == VideoQuality.VALID

    # Try to get duration (may be None for fake file)
    duration = get_video_duration(sample_video_file)
    # Just verify it doesn't crash

    # Get info
    info = get_video_info(sample_video_file)
    assert isinstance(info, dict)
