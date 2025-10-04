"""
Path Utilities

Helper functions for path validation and directory operations.
"""

import logging
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


def validate_path(path: Path, must_exist: bool = False) -> bool:
    """
    Validate a path.

    Args:
        path: Path to validate
        must_exist: If True, path must already exist

    Returns:
        True if valid

    Example:
        if validate_path(Path("/home/pi/videos")):
            print("Valid path")
    """
    if not isinstance(path, Path):
        logger.error(f"Invalid path type: {type(path)}")
        return False

    if must_exist and not path.exists():
        logger.error(f"Path does not exist: {path}")
        return False

    # Check if path is absolute
    if not path.is_absolute():
        logger.warning(f"Path is not absolute: {path}")
        return False

    return True


def ensure_directory(path: Path, create: bool = True) -> bool:
    """
    Ensure directory exists.

    Args:
        path: Directory path
        create: If True, create if doesn't exist

    Returns:
        True if directory exists or was created

    Example:
        ensure_directory(Path("/home/pi/videos"))
    """
    try:
        if path.exists():
            if not path.is_dir():
                logger.error(f"Path exists but is not a directory: {path}")
                return False
            return True

        if create:
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {path}")
            return True

        return False

    except OSError as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False


def safe_filename(filename: str) -> str:
    """
    Make filename safe by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Safe filename

    Example:
        safe = safe_filename("video:with*bad?chars.mp4")
        # Returns: "video_with_bad_chars.mp4"
    """
    # Replace invalid characters with underscore
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    safe = filename

    for char in invalid_chars:
        safe = safe.replace(char, '_')

    return safe


def get_file_extension(path: Path) -> str:
    """
    Get file extension (lowercase, without dot).

    Args:
        path: File path

    Returns:
        Extension string

    Example:
        ext = get_file_extension(Path("video.MP4"))
        # Returns: "mp4"
    """
    return path.suffix.lower().lstrip('.')


def is_video_file(path: Path) -> bool:
    """
    Check if file is a video based on extension.

    Args:
        path: File path

    Returns:
        True if video file
    """
    video_extensions = ['mp4', 'avi', 'mkv', 'mov', 'flv', 'wmv', 'webm']
    ext = get_file_extension(path)
    return ext in video_extensions


def get_relative_path(path: Path, base: Path) -> Optional[Path]:
    """
    Get relative path from base.

    Args:
        path: Full path
        base: Base path

    Returns:
        Relative path, or None if not relative to base

    Example:
        rel = get_relative_path(
            Path("/home/pi/videos/pending/video.mp4"),
            Path("/home/pi/videos")
        )
        # Returns: Path("pending/video.mp4")
    """
    try:
        return path.relative_to(base)
    except ValueError:
        return None


def format_size(bytes: int) -> str:
    """
    Format byte size as human-readable string.

    Args:
        bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 GB")

    Example:
        print(format_size(1_500_000_000))  # "1.40 GB"
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} PB"


def format_duration(seconds: int) -> str:
    """
    Format duration as human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "10:30")

    Example:
        print(format_duration(630))  # "10:30"
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def calculate_directory_size(directory: Path) -> int:
    """
    Calculate total size of all files in directory.

    Args:
        directory: Directory path

    Returns:
        Total size in bytes
    """
    total = 0
    try:
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                total += file_path.stat().st_size
    except OSError as e:
        logger.warning(f"Error calculating directory size: {e}")

    return total


def is_path_writable(path: Path) -> bool:
    """
    Test if path is writable.

    Args:
        path: Path to test

    Returns:
        True if writable
    """
    try:
        # For directories, try creating a temp file
        if path.is_dir():
            test_file = path / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True

        # For files, check parent directory
        return is_path_writable(path.parent)

    except OSError:
        return False
