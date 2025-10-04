"""
Recording Utilities

Shared utility functions for recording operations.
Extracted here to follow DRY (Don't Repeat Yourself) principle.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from recording.constants import FILENAME_FORMAT, MIN_FREE_SPACE_GB


def generate_filename(
    base_path: Path,
    format_string: str = FILENAME_FORMAT,
    extension: str = "mp4"
) -> Path:
    """
    Generate timestamped filename for recording.

    Creates unique filename based on current timestamp.

    Args:
        base_path: Directory where file will be saved
        format_string: strftime format for filename
        extension: File extension (default: "mp4")

    Returns:
        Complete file path with timestamp

    Example:
        path = generate_filename(Path("/recordings"))
        # Returns: /recordings/recording_2025-01-15_143022.mp4
    """
    timestamp = datetime.now().strftime(format_string)
    filename = f"{timestamp}.{extension}"
    return base_path / filename


def check_disk_space(path: Path, required_gb: float = MIN_FREE_SPACE_GB) -> bool:
    """
    Check if sufficient disk space is available.

    Args:
        path: Path to check (file or directory)
        required_gb: Minimum required space in GB

    Returns:
        True if enough space available, False otherwise

    Example:
        if not check_disk_space(Path("/recordings"), required_gb=5.0):
            print("Not enough disk space!")
    """
    try:
        # Get disk usage statistics
        stat = shutil.disk_usage(path)

        # Convert bytes to GB
        free_gb = stat.free / (1024 ** 3)

        return free_gb >= required_gb

    except Exception as e:
        logging.error(f"Error checking disk space: {e}")
        return False


def get_disk_space_info(path: Path) -> dict:
    """
    Get detailed disk space information.

    Args:
        path: Path to check

    Returns:
        Dictionary with disk space information in GB
        {
            'total_gb': float,
            'used_gb': float,
            'free_gb': float,
            'percent_used': float
        }

    Example:
        info = get_disk_space_info(Path("/recordings"))
        print(f"Free space: {info['free_gb']:.1f} GB")
    """
    try:
        stat = shutil.disk_usage(path)

        total_gb = stat.total / (1024 ** 3)
        used_gb = stat.used / (1024 ** 3)
        free_gb = stat.free / (1024 ** 3)
        percent_used = (stat.used / stat.total) * 100

        return {
            'total_gb': total_gb,
            'used_gb': used_gb,
            'free_gb': free_gb,
            'percent_used': percent_used
        }

    except Exception as e:
        logging.error(f"Error getting disk space info: {e}")
        return {
            'total_gb': 0.0,
            'used_gb': 0.0,
            'free_gb': 0.0,
            'percent_used': 0.0
        }


def validate_output_path(path: Path) -> tuple[bool, Optional[str]]:
    """
    Validate output path for recording.

    Checks:
    - Path is writable
    - Parent directory exists or can be created
    - Sufficient disk space

    Args:
        path: Output file path to validate

    Returns:
        Tuple of (is_valid, error_message)
        error_message is None if valid

    Example:
        valid, error = validate_output_path(Path("/recordings/video.mp4"))
        if not valid:
            print(f"Invalid path: {error}")
    """
    # Check if parent directory exists
    parent = path.parent
    if not parent.exists():
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return False, f"Cannot create directory: {e}"

    # Check if directory is writable
    if not parent.is_dir():
        return False, f"Parent path is not a directory: {parent}"

    # Try to write a test file
    test_file = parent / ".write_test"
    try:
        test_file.touch()
        test_file.unlink()
    except Exception as e:
        return False, f"Directory not writable: {e}"

    # Check disk space
    if not check_disk_space(parent):
        return False, f"Insufficient disk space (need {MIN_FREE_SPACE_GB} GB)"

    return True, None


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "42.3 MB", "1.2 GB")

    Example:
        size = format_file_size(45000000)
        print(size)  # "42.9 MB"
    """
    # Handle negative or zero
    if size_bytes <= 0:
        return "0 B"

    # Units
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)

    # Find appropriate unit
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1

    # Format with appropriate precision
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def cleanup_old_recordings(
    directory: Path,
    keep_count: int = 10,
    max_age_days: Optional[int] = None
) -> int:
    """
    Clean up old recording files.

    Removes oldest recordings when directory has too many files.
    Useful for automatic cleanup to prevent disk from filling.

    Args:
        directory: Directory containing recordings
        keep_count: Number of most recent files to keep
        max_age_days: Optional max age in days (delete older)

    Returns:
        Number of files deleted

    Example:
        deleted = cleanup_old_recordings(Path("/recordings"), keep_count=10)
        print(f"Deleted {deleted} old recordings")
    """
    if not directory.exists():
        return 0

    # Get all video files
    video_files = []
    for ext in ['.mp4', '.avi', '.mkv']:
        video_files.extend(directory.glob(f"*{ext}"))

    # Sort by modification time (oldest first)
    video_files.sort(key=lambda p: p.stat().st_mtime)

    deleted_count = 0

    # Delete by age if specified
    if max_age_days:
        import time
        max_age_seconds = max_age_days * 24 * 60 * 60
        current_time = time.time()

        for file_path in video_files[:]:  # Copy list for iteration
            file_age = current_time - file_path.stat().st_mtime
            if file_age > max_age_seconds:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    video_files.remove(file_path)
                    logging.info(f"Deleted old recording: {file_path.name}")
                except Exception as e:
                    logging.error(f"Failed to delete {file_path}: {e}")

    # Delete oldest files if too many
    if len(video_files) > keep_count:
        files_to_delete = video_files[:-keep_count]  # All except newest keep_count

        for file_path in files_to_delete:
            try:
                file_path.unlink()
                deleted_count += 1
                logging.info(f"Deleted old recording: {file_path.name}")
            except Exception as e:
                logging.error(f"Failed to delete {file_path}: {e}")

    return deleted_count


def get_recording_files(directory: Path, pattern: str = "*.mp4") -> list[Path]:
    """
    Get list of recording files in directory.

    Args:
        directory: Directory to search
        pattern: Glob pattern for matching files

    Returns:
        List of file paths, sorted by modification time (newest first)

    Example:
        files = get_recording_files(Path("/recordings"))
        for file in files:
            print(file.name)
    """
    if not directory.exists():
        return []

    # Find matching files
    files = list(directory.glob(pattern))

    # Sort by modification time (newest first)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    return files


def safe_filename(name: str, max_length: int = 255) -> str:
    """
    Sanitize filename to remove invalid characters.

    Removes characters that are invalid in filenames on most systems.

    Args:
        name: Original filename
        max_length: Maximum filename length

    Returns:
        Sanitized filename

    Example:
        safe = safe_filename("video: test/recording.mp4")
        # Returns: "video_test_recording.mp4"
    """
    # Replace invalid characters with underscore
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')

    # Remove leading/trailing dots and spaces
    name = name.strip('. ')

    # Truncate if too long
    if len(name) > max_length:
        # Try to preserve extension
        parts = name.rsplit('.', 1)
        if len(parts) == 2:
            base, ext = parts
            max_base_len = max_length - len(ext) - 1
            name = f"{base[:max_base_len]}.{ext}"
        else:
            name = name[:max_length]

    return name


def get_cpu_temperature() -> Optional[float]:
    """
    Get CPU temperature (Raspberry Pi specific).

    Reads from /sys/class/thermal/thermal_zone0/temp

    Returns:
        Temperature in Celsius, or None if unavailable

    Example:
        temp = get_cpu_temperature()
        if temp and temp > 75:
            print("Warning: CPU is hot!")
    """
    try:
        temp_file = Path("/sys/class/thermal/thermal_zone0/temp")
        if temp_file.exists():
            temp_millidegrees = int(temp_file.read_text().strip())
            return temp_millidegrees / 1000.0
    except Exception as e:
        logging.debug(f"Could not read CPU temperature: {e}")

    return None


def estimate_recording_size(duration_seconds: float, fps: int = 30) -> float:
    """
    Estimate recording file size.

    Based on h264 encoding at typical bitrates.

    Args:
        duration_seconds: Recording duration
        fps: Frame rate

    Returns:
        Estimated size in MB

    Example:
        size_mb = estimate_recording_size(600)  # 10 minutes
        print(f"Estimated size: {size_mb:.0f} MB")
    """
    # Rough estimates for h264 @ CRF 23, 1080p
    # Varies based on content complexity
    minutes = duration_seconds / 60
    mb_per_minute = 4.0  # Conservative estimate

    return minutes * mb_per_minute
