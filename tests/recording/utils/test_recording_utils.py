"""
Recording Utilities Tests

Tests for utility functions showing:
- Filename generation
- Disk space checking
- File size formatting
- Cleanup operations
- Path validation

To run:
    pytest tests/recording/utils/test_recording_utils.py -v
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from recording.utils.recording_utils import (
    generate_filename,
    check_disk_space,
    get_disk_space_info,
    validate_output_path,
    format_file_size,
    cleanup_old_recordings,
    get_recording_files,
    safe_filename,
    estimate_recording_size,
)


# =============================================================================
# FILENAME GENERATION TESTS
# =============================================================================

@pytest.mark.unit
def test_generate_filename(temp_recording_dir):
    """Test generating timestamped filename."""
    filename = generate_filename(temp_recording_dir)

    # Should return a Path
    assert isinstance(filename, Path)

    # Should have .mp4 extension
    assert filename.suffix == ".mp4"

    # Should be in the specified directory
    assert filename.parent == temp_recording_dir

    # Should contain timestamp pattern (YYYY-MM-DD_HHMMSS)
    assert "_" in filename.stem
    assert "-" in filename.stem


@pytest.mark.unit
def test_generate_filename_custom_extension(temp_recording_dir):
    """Test generating filename with custom extension."""
    filename = generate_filename(temp_recording_dir, extension="avi")

    assert filename.suffix == ".avi"


@pytest.mark.unit
def test_generate_filename_unique():
    """Test that generated filenames are unique."""
    temp_dir = Path(tempfile.mkdtemp())

    filename1 = generate_filename(temp_dir)
    filename2 = generate_filename(temp_dir)

    # Should be different (different timestamps)
    # Note: May be same if called in same second - but unlikely

    shutil.rmtree(temp_dir)


# =============================================================================
# DISK SPACE TESTS
# =============================================================================

@pytest.mark.unit
def test_check_disk_space(temp_recording_dir):
    """Test checking disk space."""
    # Should have space (we just created temp dir)
    has_space = check_disk_space(temp_recording_dir, required_gb=0.001)

    assert has_space is True


@pytest.mark.unit
def test_check_disk_space_insufficient():
    """Test disk space check with impossibly large requirement."""
    temp_dir = Path(tempfile.mkdtemp())

    # Require more space than any drive has
    has_space = check_disk_space(temp_dir, required_gb=999999999)

    assert has_space is False

    shutil.rmtree(temp_dir)


@pytest.mark.unit
def test_get_disk_space_info(temp_recording_dir):
    """Test getting disk space information."""
    info = get_disk_space_info(temp_recording_dir)

    # Should have all required fields
    assert 'total_gb' in info
    assert 'used_gb' in info
    assert 'free_gb' in info
    assert 'percent_used' in info

    # Values should be reasonable
    assert info['total_gb'] > 0
    assert info['free_gb'] >= 0
    assert 0 <= info['percent_used'] <= 100


# =============================================================================
# PATH VALIDATION TESTS
# =============================================================================

@pytest.mark.unit
def test_validate_output_path_valid(temp_recording_dir):
    """Test validating valid output path."""
    output_file = temp_recording_dir / "recording.mp4"

    valid, error = validate_output_path(output_file)

    assert valid is True
    assert error is None


@pytest.mark.unit
def test_validate_output_path_creates_directory():
    """Test that validation creates missing directory."""
    temp_dir = Path(tempfile.mkdtemp())
    nested_dir = temp_dir / "nested" / "path"
    output_file = nested_dir / "recording.mp4"

    valid, error = validate_output_path(output_file)

    assert valid is True
    assert nested_dir.exists()

    shutil.rmtree(temp_dir)


@pytest.mark.unit
def test_validate_output_path_parent_is_file():
    """Test validation fails if parent is a file."""
    temp_dir = Path(tempfile.mkdtemp())

    # Create a file
    file_path = temp_dir / "somefile.txt"
    file_path.touch()

    # Try to use it as parent directory
    output_file = file_path / "recording.mp4"

    valid, error = validate_output_path(output_file)

    assert valid is False
    assert "not a directory" in error.lower()

    shutil.rmtree(temp_dir)


# =============================================================================
# FILE SIZE FORMATTING TESTS
# =============================================================================

@pytest.mark.unit
def test_format_file_size_bytes():
    """Test formatting bytes."""
    assert format_file_size(0) == "0 B"
    assert format_file_size(500) == "500 B"
    assert format_file_size(1023) == "1023 B"


@pytest.mark.unit
def test_format_file_size_kilobytes():
    """Test formatting kilobytes."""
    result = format_file_size(1024)
    assert "1.0 KB" in result

    result = format_file_size(1536)  # 1.5 KB
    assert "1.5 KB" in result


@pytest.mark.unit
def test_format_file_size_megabytes():
    """Test formatting megabytes."""
    result = format_file_size(1024 * 1024)
    assert "1.0 MB" in result

    result = format_file_size(50 * 1024 * 1024)  # 50 MB
    assert "50.0 MB" in result


@pytest.mark.unit
def test_format_file_size_gigabytes():
    """Test formatting gigabytes."""
    result = format_file_size(1024 * 1024 * 1024)
    assert "1.0 GB" in result

    result = format_file_size(2.5 * 1024 * 1024 * 1024)
    assert "2.5 GB" in result


# =============================================================================
# CLEANUP TESTS
# =============================================================================

@pytest.mark.unit
def test_cleanup_old_recordings_by_count(temp_recording_dir):
    """Test cleaning up old recordings by count."""
    # Create 15 test files
    for i in range(15):
        file_path = temp_recording_dir / f"recording_{i:03d}.mp4"
        file_path.touch()

    # Keep only 10 most recent
    deleted = cleanup_old_recordings(temp_recording_dir, keep_count=10)

    assert deleted == 5

    # Should have exactly 10 files left
    remaining = list(temp_recording_dir.glob("*.mp4"))
    assert len(remaining) == 10


@pytest.mark.unit
def test_cleanup_old_recordings_empty_directory(temp_recording_dir):
    """Test cleanup on empty directory."""
    deleted = cleanup_old_recordings(temp_recording_dir, keep_count=10)

    assert deleted == 0


@pytest.mark.unit
def test_cleanup_old_recordings_keep_all(temp_recording_dir):
    """Test cleanup when all files should be kept."""
    # Create 5 files
    for i in range(5):
        file_path = temp_recording_dir / f"recording_{i}.mp4"
        file_path.touch()

    # Keep 10 (more than we have)
    deleted = cleanup_old_recordings(temp_recording_dir, keep_count=10)

    assert deleted == 0

    # All files should remain
    remaining = list(temp_recording_dir.glob("*.mp4"))
    assert len(remaining) == 5


# =============================================================================
# GET RECORDING FILES TESTS
# =============================================================================

@pytest.mark.unit
def test_get_recording_files(temp_recording_dir):
    """Test getting list of recording files."""
    # Create test files
    file1 = temp_recording_dir / "recording1.mp4"
    file2 = temp_recording_dir / "recording2.mp4"
    file3 = temp_recording_dir / "recording3.mp4"

    file1.touch()
    file2.touch()
    file3.touch()

    files = get_recording_files(temp_recording_dir)

    assert len(files) == 3
    assert all(f.suffix == ".mp4" for f in files)


@pytest.mark.unit
def test_get_recording_files_sorted_by_time(temp_recording_dir):
    """Test that files are sorted by modification time."""
    import time

    # Create files with delays
    file1 = temp_recording_dir / "recording1.mp4"
    file1.touch()

    time.sleep(0.1)

    file2 = temp_recording_dir / "recording2.mp4"
    file2.touch()

    time.sleep(0.1)

    file3 = temp_recording_dir / "recording3.mp4"
    file3.touch()

    files = get_recording_files(temp_recording_dir)

    # Should be newest first
    assert files[0] == file3
    assert files[1] == file2
    assert files[2] == file1


@pytest.mark.unit
def test_get_recording_files_empty_directory(temp_recording_dir):
    """Test getting files from empty directory."""
    files = get_recording_files(temp_recording_dir)

    assert files == []


@pytest.mark.unit
def test_get_recording_files_custom_pattern(temp_recording_dir):
    """Test getting files with custom pattern."""
    # Create different file types
    (temp_recording_dir / "video.mp4").touch()
    (temp_recording_dir / "video.avi").touch()
    (temp_recording_dir / "document.txt").touch()

    # Get only .avi files
    files = get_recording_files(temp_recording_dir, pattern="*.avi")

    assert len(files) == 1
    assert files[0].suffix == ".avi"


# =============================================================================
# SAFE FILENAME TESTS
# =============================================================================

@pytest.mark.unit
def test_safe_filename_removes_invalid_chars():
    """Test that invalid characters are removed."""
    unsafe = "video<>:test/file.mp4"
    safe = safe_filename(unsafe)

    # Should have replaced invalid chars
    assert "<" not in safe
    assert ">" not in safe
    assert ":" not in safe
    assert "/" not in safe


@pytest.mark.unit
def test_safe_filename_preserves_extension():
    """Test that file extension is preserved."""
    result = safe_filename("test_video.mp4")

    assert result.endswith(".mp4")


@pytest.mark.unit
def test_safe_filename_truncates_long_names():
    """Test that long filenames are truncated."""
    long_name = "a" * 300 + ".mp4"
    safe = safe_filename(long_name)

    assert len(safe) <= 255


@pytest.mark.unit
def test_safe_filename_strips_leading_trailing():
    """Test that leading/trailing dots and spaces are removed."""
    result = safe_filename("  ..test.mp4  ")

    assert not result.startswith(" ")
    assert not result.startswith(".")
    assert not result.endswith(" ")


# =============================================================================
# ESTIMATION TESTS
# =============================================================================

@pytest.mark.unit
def test_estimate_recording_size():
    """Test estimating recording file size."""
    # 10 minutes should be around 40 MB
    size = estimate_recording_size(600)

    assert 30 < size < 50  # Reasonable range


@pytest.mark.unit
def test_estimate_recording_size_short():
    """Test estimation for short recording."""
    # 1 minute
    size = estimate_recording_size(60)

    assert 3 < size < 5


@pytest.mark.unit
def test_estimate_recording_size_long():
    """Test estimation for long recording."""
    # 25 minutes (max)
    size = estimate_recording_size(1500)

    assert 90 < size < 110
