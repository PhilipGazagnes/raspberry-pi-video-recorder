"""
Recording Constants

Centralized configuration for video recording system.
All magic numbers, timing values, and FFmpeg settings in one place.

Why separate constants?
- Easy to tune recording behavior
- Clear documentation of system limits
- Type safety with enums
- Single source of truth
"""

from enum import Enum
from pathlib import Path

# =============================================================================
# RECORDING DURATION CONFIGURATION
# =============================================================================

# Default recording duration in seconds
# 10 minutes is a typical sparring round duration
DEFAULT_RECORDING_DURATION = 600  # 10 minutes

# Extension duration when user double-presses button
# 5 minutes allows for extended rounds
EXTENSION_DURATION = 300  # 5 minutes

# Maximum total recording duration
# 25 minutes = 10 + 3 extensions (safety limit to prevent filling disk)
MAX_RECORDING_DURATION = 1500  # 25 minutes

# Warning time before recording ends
# 1 minute gives user time to decide on extension
WARNING_TIME = 60  # 1 minute (triggers at 9:00 remaining)


# =============================================================================
# VIDEO CAPTURE CONFIGURATION
# =============================================================================

# Video resolution (width x height)
# 1920x1080 = Full HD, good balance of quality and file size
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080

# Frame rate in frames per second
# 30 FPS is smooth for sports analysis, lower than 60 to save space
VIDEO_FPS = 30

# Video codec for encoding
# h264 is widely supported, good compression, hardware accelerated on Pi
VIDEO_CODEC = "libx264"

# Encoding preset for h264
# "ultrafast" prioritizes speed over compression
# Good for Pi 5 - real-time encoding without dropping frames
# Options: ultrafast, superfast, veryfast, faster, fast, medium, slow
VIDEO_PRESET = "ultrafast"

# Constant Rate Factor (quality setting)
# Lower = better quality, larger files
# 23 is default, 18-28 is typical range
# 23 is visually lossless for most content
VIDEO_CRF = 23

# Video container format
# mp4 is universally compatible, good for YouTube upload
VIDEO_FORMAT = "mp4"


# =============================================================================
# AUDIO CAPTURE CONFIGURATION (Future Enhancement)
# =============================================================================

# Whether to capture audio with video
# False for v1 (no audio recording), True for future versions
CAPTURE_AUDIO = False

# Audio codec (if audio enabled)
AUDIO_CODEC = "aac"

# Audio bitrate
AUDIO_BITRATE = "128k"


# =============================================================================
# CAMERA DEVICE CONFIGURATION
# =============================================================================

# Default camera device path
# /dev/video0 is typically the first USB webcam on Linux
# Can be overridden at runtime if multiple cameras
DEFAULT_CAMERA_DEVICE = "/dev/video0"

# Video input format
# v4l2 is Video4Linux2, standard Linux video capture API
VIDEO_INPUT_FORMAT = "v4l2"

# Camera warmup time in seconds
# Brief delay after opening camera before recording starts
# Allows auto-exposure and auto-focus to stabilize
CAMERA_WARMUP_TIME = 1.0


# =============================================================================
# STORAGE CONFIGURATION
# =============================================================================

# Base directory for storing recordings
# Will be created if doesn't exist
DEFAULT_STORAGE_PATH = Path("/home/pi/recordings")

# Filename format using strftime format codes
# Example: "recording_2025-01-15_143022.mp4"
FILENAME_FORMAT = "recording_%Y-%m-%d_%H%M%S"

# Minimum free disk space in GB before refusing to record
# 5 GB ensures space for at least 2-3 recordings
MIN_FREE_SPACE_GB = 5.0


# =============================================================================
# FFMPEG COMMAND CONFIGURATION
# =============================================================================

# FFmpeg log level
# "error" only shows errors, keeps output clean
# Options: quiet, panic, fatal, error, warning, info, verbose, debug
FFMPEG_LOG_LEVEL = "error"

# Buffer size for video capture
# Larger buffer helps prevent frame drops
CAPTURE_BUFFER_SIZE = "10M"

# Input thread queue size
# Higher value helps with USB camera latency
THREAD_QUEUE_SIZE = 512


# =============================================================================
# RECORDING STATE TRACKING
# =============================================================================

class RecordingState(Enum):
    """
    States a recording session can be in.

    Lifecycle: IDLE -> STARTING -> RECORDING -> STOPPING -> IDLE
    """
    IDLE = "idle"              # No recording active
    STARTING = "starting"      # Camera warming up, preparing to record
    RECORDING = "recording"    # Actively recording video
    STOPPING = "stopping"      # Finalizing recording, closing file
    ERROR = "error"           # Recording failed


# =============================================================================
# ERROR CODES
# =============================================================================

class RecordingError(Enum):
    """
    Error conditions that can occur during recording.

    Used for specific error handling and user feedback.
    """
    CAMERA_NOT_FOUND = "camera_not_found"
    CAMERA_BUSY = "camera_busy"
    STORAGE_FULL = "storage_full"
    FFMPEG_ERROR = "ffmpeg_error"
    DURATION_EXCEEDED = "duration_exceeded"
    UNKNOWN_ERROR = "unknown_error"


# =============================================================================
# HEALTH CHECK CONFIGURATION
# =============================================================================

# How often to check recording health (seconds)
# Quick checks during recording to detect issues
HEALTH_CHECK_INTERVAL = 5.0

# Maximum time without new frames before considering recording stalled
STALL_TIMEOUT = 10.0

# Maximum CPU temperature before warning (Celsius)
# Pi 5 throttles at 80°C, warn at 75°C
MAX_CPU_TEMP = 75.0


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_ffmpeg_command(
    input_device: str,
    output_file: str,
    width: int = VIDEO_WIDTH,
    height: int = VIDEO_HEIGHT,
    fps: int = VIDEO_FPS
) -> list[str]:
    """
    Generate FFmpeg command for video capture.

    This creates the command-line arguments for FFmpeg to capture
    video from a USB webcam and encode it to a file.

    Args:
        input_device: Camera device path (e.g., /dev/video0)
        output_file: Output filename with path
        width: Video width in pixels
        height: Video height in pixels
        fps: Frame rate

    Returns:
        List of command arguments for subprocess

    Example:
        cmd = get_ffmpeg_command("/dev/video0", "output.mp4")
        subprocess.Popen(cmd)
    """
    command = [
        "ffmpeg",

        # Input options
        "-f", VIDEO_INPUT_FORMAT,              # Video4Linux2 input
        "-input_format", "mjpeg",              # MJPEG from camera (less CPU than raw)
        "-video_size", f"{width}x{height}",    # Resolution
        "-framerate", str(fps),                # Frame rate
        "-thread_queue_size", str(THREAD_QUEUE_SIZE),  # Buffer size
        "-i", input_device,                    # Input device

        # Output options
        "-c:v", VIDEO_CODEC,                   # H264 video codec
        "-preset", VIDEO_PRESET,               # Encoding speed
        "-crf", str(VIDEO_CRF),                # Quality level
        "-pix_fmt", "yuv420p",                 # Pixel format (compatible)
        "-movflags", "+faststart",             # Optimize for streaming

        # Logging
        "-loglevel", FFMPEG_LOG_LEVEL,

        # Output file (overwrite if exists)
        "-y",
        output_file
    ]

    return command


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "10:00", "1:30")

    Example:
        format_duration(630) -> "10:30"
        format_duration(90) -> "1:30"
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def calculate_file_size_estimate(duration_seconds: float) -> float:
    """
    Estimate recording file size in MB.

    Based on h264 encoding at CRF 23, 1080p @ 30fps.
    Rough estimate: ~3-5 MB per minute depending on motion.

    Args:
        duration_seconds: Recording duration in seconds

    Returns:
        Estimated file size in megabytes

    Example:
        calculate_file_size_estimate(600) -> ~40 MB
    """
    minutes = duration_seconds / 60
    # Conservative estimate: 4 MB per minute for 1080p h264
    mb_per_minute = 4.0
    return minutes * mb_per_minute


def validate_camera_device(device_path: str) -> bool:
    """
    Check if camera device exists and is accessible.

    Args:
        device_path: Path to camera device (e.g., /dev/video0)

    Returns:
        True if device exists, False otherwise

    Example:
        if validate_camera_device("/dev/video0"):
            print("Camera found!")
    """
    from pathlib import Path
    device = Path(device_path)
    return device.exists() and device.is_char_device()
