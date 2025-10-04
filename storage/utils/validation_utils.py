"""
Validation Utilities

Functions for validating video files.
Uses ffmpeg to probe video files for integrity.
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from storage.constants import (
    MIN_VIDEO_SIZE_BYTES,
    VALIDATION_TIMEOUT_SECONDS,
    VideoQuality,
)


logger = logging.getLogger(__name__)


def validate_video_file(
    file_path: Path,
    enable_ffmpeg: bool = True,
    min_size: int = MIN_VIDEO_SIZE_BYTES
) -> Tuple[VideoQuality, Optional[str]]:
    """
    Validate video file integrity.

    Performs multiple checks:
    1. File exists
    2. File size >= minimum
    3. FFmpeg can read the file (if enabled)

    Args:
        file_path: Path to video file
        enable_ffmpeg: If True, use ffmpeg probe for validation
        min_size: Minimum valid file size in bytes

    Returns:
        Tuple of (VideoQuality, error_message)

    Example:
        quality, error = validate_video_file(Path("/path/to/video.mp4"))
        if quality == VideoQuality.VALID:
            print("Video is good!")
        else:
            print(f"Video problem: {error}")
    """
    # Check file exists
    if not file_path.exists():
        return VideoQuality.CORRUPTED, f"File not found: {file_path}"

    # Check file size
    try:
        file_size = file_path.stat().st_size
    except OSError as e:
        return VideoQuality.CORRUPTED, f"Cannot read file: {e}"

    if file_size < min_size:
        size_mb = file_size / (1024 ** 2)
        min_mb = min_size / (1024 ** 2)
        return (
            VideoQuality.TOO_SMALL,
            f"File too small: {size_mb:.2f} MB (minimum: {min_mb:.2f} MB)"
        )

    # FFmpeg validation (if enabled)
    if enable_ffmpeg:
        quality, error = validate_with_ffmpeg(file_path)
        if quality != VideoQuality.VALID:
            return quality, error

    # All checks passed
    return VideoQuality.VALID, None


def validate_with_ffmpeg(file_path: Path) -> Tuple[VideoQuality, Optional[str]]:
    """
    Validate video file using ffmpeg probe.

    Uses ffprobe to check if the file is a valid video format
    and can be read without errors.

    Args:
        file_path: Path to video file

    Returns:
        Tuple of (VideoQuality, error_message)
    """
    try:
        # Check if ffprobe is available
        result = subprocess.run(
            ['ffprobe', '-version'],
            capture_output=True,
            timeout=5,
            check=False
        )

        if result.returncode != 0:
            logger.warning("ffprobe not available, skipping advanced validation")
            return VideoQuality.VALID, None

    except FileNotFoundError:
        logger.warning("ffprobe not found in PATH, skipping advanced validation")
        return VideoQuality.VALID, None
    except subprocess.TimeoutExpired:
        logger.warning("ffprobe version check timeout")
        return VideoQuality.VALID, None

    # Probe video file
    try:
        result = subprocess.run(
            [
                'ffprobe',
                '-v', 'error',
                '-show_format',
                '-show_streams',
                '-print_format', 'json',
                str(file_path)
            ],
            capture_output=True,
            timeout=VALIDATION_TIMEOUT_SECONDS,
            text=True,
            check=False
        )

        # Check for errors in stderr
        if result.returncode != 0 or result.stderr:
            error_msg = result.stderr.strip() if result.stderr else "ffprobe failed"
            logger.debug(f"ffprobe error for {file_path.name}: {error_msg}")
            return VideoQuality.CORRUPTED, f"FFmpeg validation failed: {error_msg}"

        # Parse JSON output
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            return VideoQuality.INVALID_FORMAT, f"Invalid ffprobe output: {e}"

        # Check for format information
        if 'format' not in data:
            return VideoQuality.INVALID_FORMAT, "No format information found"

        # Check for video streams
        streams = data.get('streams', [])
        has_video = any(s.get('codec_type') == 'video' for s in streams)

        if not has_video:
            return VideoQuality.INVALID_FORMAT, "No video stream found"

        # Video is valid
        logger.debug(f"Video validated successfully: {file_path.name}")
        return VideoQuality.VALID, None

    except subprocess.TimeoutExpired:
        return (
            VideoQuality.CORRUPTED,
            f"Validation timeout after {VALIDATION_TIMEOUT_SECONDS}s"
        )
    except Exception as e:
        logger.error(f"Error during ffmpeg validation: {e}")
        return VideoQuality.CORRUPTED, f"Validation error: {e}"


def get_video_duration(file_path: Path) -> Optional[int]:
    """
    Get video duration in seconds using ffprobe.

    Args:
        file_path: Path to video file

    Returns:
        Duration in seconds, or None if unable to determine

    Example:
        duration = get_video_duration(Path("/path/to/video.mp4"))
        if duration:
            print(f"Video is {duration} seconds long")
    """
    try:
        result = subprocess.run(
            [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'json',
                str(file_path)
            ],
            capture_output=True,
            timeout=VALIDATION_TIMEOUT_SECONDS,
            text=True,
            check=False
        )

        if result.returncode != 0:
            logger.warning(f"Failed to get duration for {file_path.name}")
            return None

        data = json.loads(result.stdout)
        duration_str = data.get('format', {}).get('duration')

        if duration_str:
            return int(float(duration_str))

        return None

    except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError, Exception) as e:
        logger.warning(f"Error getting video duration: {e}")
        return None


def get_video_info(file_path: Path) -> dict:
    """
    Get detailed video information using ffprobe.

    Args:
        file_path: Path to video file

    Returns:
        Dictionary with video information (or empty dict if failed)

    Example:
        info = get_video_info(Path("/path/to/video.mp4"))
        print(f"Resolution: {info.get('width')}x{info.get('height')}")
        print(f"Codec: {info.get('codec_name')}")
    """
    try:
        result = subprocess.run(
            [
                'ffprobe',
                '-v', 'error',
                '-show_format',
                '-show_streams',
                '-of', 'json',
                str(file_path)
            ],
            capture_output=True,
            timeout=VALIDATION_TIMEOUT_SECONDS,
            text=True,
            check=False
        )

        if result.returncode != 0:
            return {}

        data = json.loads(result.stdout)

        # Extract useful information
        format_info = data.get('format', {})
        streams = data.get('streams', [])

        # Find video stream
        video_stream = next(
            (s for s in streams if s.get('codec_type') == 'video'),
            None
        )

        info = {
            'duration': float(format_info.get('duration', 0)),
            'size': int(format_info.get('size', 0)),
            'bit_rate': int(format_info.get('bit_rate', 0)),
            'format_name': format_info.get('format_name', ''),
        }

        if video_stream:
            info.update({
                'codec_name': video_stream.get('codec_name', ''),
                'width': video_stream.get('width', 0),
                'height': video_stream.get('height', 0),
                'fps': eval_fps(video_stream.get('r_frame_rate', '0/0')),
            })

        return info

    except Exception as e:
        logger.warning(f"Error getting video info: {e}")
        return {}


def eval_fps(fps_str: str) -> float:
    """
    Evaluate frame rate from ffprobe fraction string.

    Args:
        fps_str: Frame rate string like "30000/1001" or "30"

    Returns:
        Frame rate as float

    Example:
        fps = eval_fps("30000/1001")  # Returns 29.97
    """
    try:
        if '/' in fps_str:
            num, denom = fps_str.split('/')
            return float(num) / float(denom)
        return float(fps_str)
    except (ValueError, ZeroDivisionError):
        return 0.0


def quick_validate(file_path: Path) -> bool:
    """
    Quick validation - just checks file exists and has minimum size.

    Use this for fast checks without ffmpeg overhead.

    Args:
        file_path: Path to video file

    Returns:
        True if file passes basic checks

    Example:
        if quick_validate(video_path):
            # File exists and has reasonable size
            proceed_with_upload()
    """
    if not file_path.exists():
        return False

    try:
        file_size = file_path.stat().st_size
        return file_size >= MIN_VIDEO_SIZE_BYTES
    except OSError:
        return False
