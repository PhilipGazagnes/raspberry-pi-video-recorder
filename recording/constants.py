"""
Recording Constants

Centralized configuration for video recording system.
All magic numbers, timing values, and FFmpeg settings in one place.

Why separate constants?
- Easy to tune recording behavior
- Clear documentation of system limits
- Type safety with enums
- Single source of truth

Note: Configuration values (durations, video settings, etc.) have been moved to
config/settings.py per CLAUDE.md guidelines. This file now contains only
enums, FFmpeg-specific constants, and utility functions.
"""

from enum import Enum
from pathlib import Path

from config.settings import (
    AUDIO_BITRATE,
    AUDIO_CHANNELS,
    AUDIO_CODEC,
    AUDIO_INPUT_DEVICE,
    AUDIO_INPUT_FORMAT,
    AUDIO_SAMPLE_RATE,
    VIDEO_CODEC,
    VIDEO_CRF,
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_PRESET,
    VIDEO_WIDTH,
)

# =============================================================================
# RECORDING DURATION CONFIGURATION
# =============================================================================
# NOTE: Duration settings moved to config/settings.py
# Import from there: DEFAULT_RECORDING_DURATION, EXTENSION_DURATION,
# MAX_RECORDING_DURATION, WARNING_TIME


# =============================================================================
# VIDEO CAPTURE CONFIGURATION
# =============================================================================
# NOTE: Video settings moved to config/settings.py
# Import from there: VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS, VIDEO_CODEC,
# VIDEO_PRESET, VIDEO_CRF, VIDEO_FORMAT


# =============================================================================
# AUDIO CAPTURE CONFIGURATION
# =============================================================================

# Whether to capture audio with video
# Camera has built-in microphone (card 2: H264 USB Camera)
CAPTURE_AUDIO = True


# =============================================================================
# CAMERA DEVICE CONFIGURATION
# =============================================================================
# NOTE: Camera settings moved to config/settings.py
# Import from there: DEFAULT_CAMERA_DEVICE, CAMERA_WARMUP_TIME

# Video input format
# v4l2 is Video4Linux2, standard Linux video capture API
VIDEO_INPUT_FORMAT = "v4l2"


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

# WHY 10M buffer size: Absorbs temporary USB/storage slowdowns without
#   dropping frames
# Context: Video data flows from USB camera -> FFmpeg -> disk. If any stage
#   stalls briefly, buffer prevents frame loss. Raspberry Pi has several
#   potential bottlenecks:
#   1) USB bus contention (shared with other devices)
#   2) SD card write speed variations (wear leveling, garbage collection)
#   3) CPU load spikes (thermal throttling, background processes)
# Tradeoff: Memory vs reliability - 10M uses ~10MB RAM but provides
#   ~0.3-0.5 second buffer at 1080p30 (~20-30 MB/s bitrate depending on
#   scene complexity)
# Calculation: At 30fps, ~4MB/min compressed, 10M buffer ≈ 2.5 minutes raw,
#   0.3s compressed. This handles typical SD card write stalls (100-300ms)
# Risk: Too small (< 5M) = frame drops during brief stalls
#   Too large (> 50M) = excessive memory usage, delayed error detection
# Alternative: Could use default (smaller) buffer, but frame drops are
#   unacceptable for recording sports videos where every moment matters
CAPTURE_BUFFER_SIZE = "10M"

# WHY 512 input queue size: Reduces frame drops from USB camera timing
#   jitter
# Context: USB cameras send frames at variable intervals due to:
#   1) USB protocol overhead and bus arbitration
#   2) Camera's internal processing variations
#   3) USB host controller scheduling
#   The queue decouples camera timing from FFmpeg processing timing
# Tradeoff: Memory vs frame drop protection - Each queue slot holds a frame
#   pointer (~bytes). 512 slots ≈ 17 seconds of frames at 30fps, but actual
#   memory is minimal
# Calculation: 512 frames ÷ 30fps = ~17 seconds of buffering capacity
#   Actual memory usage is small (pointers + metadata), not full frame data
# Risk: Too small (< 128) = FFmpeg can't keep up with camera burst delivery,
#   drops frames
#   Too large (> 2048) = Increased latency if we want to stop recording
#   quickly (must drain queue first)
# Source: FFmpeg documentation recommends 512-1024 for USB cameras
# Alternative: Default queue size is 8, which is far too small for USB
#   cameras
THREAD_QUEUE_SIZE = 512


# =============================================================================
# RECORDING STATE TRACKING
# =============================================================================


class RecordingState(Enum):
    """
    States a recording session can be in.

    Lifecycle: IDLE -> STARTING -> RECORDING -> STOPPING -> IDLE
    """

    IDLE = "idle"  # No recording active
    STARTING = "starting"  # Camera warming up, preparing to record
    RECORDING = "recording"  # Actively recording video
    STOPPING = "stopping"  # Finalizing recording, closing file
    ERROR = "error"  # Recording failed


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
    fps: int = VIDEO_FPS,
) -> list[str]:
    """
    Generate FFmpeg command for video capture.

    This creates the command-line arguments for FFmpeg to capture
    video from a USB webcam and encode it to a file.
    If CAPTURE_AUDIO is enabled, also captures audio from camera microphone.

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
        # Video input options
        "-f",
        VIDEO_INPUT_FORMAT,  # Video4Linux2 input
        "-input_format",
        "mjpeg",  # MJPEG from camera (less CPU than raw)
        "-video_size",
        f"{width}x{height}",  # Resolution
        "-framerate",
        str(fps),  # Frame rate
        "-thread_queue_size",
        str(THREAD_QUEUE_SIZE),  # Buffer size
        "-i",
        input_device,  # Video input device
    ]

    # Add audio input if enabled
    if CAPTURE_AUDIO:
        # WHY separate audio input: Linux separates video/audio devices
        # Context: USB cameras expose video as /dev/videoN and audio via
        #   PulseAudio/ALSA. Must specify both inputs to FFmpeg
        # Using PulseAudio (not raw ALSA) for better compatibility:
        #   - PulseAudio auto-handles sample rate conversion
        #   - Automatically selects default input device (camera mic)
        #   - More robust than raw ALSA hw:X,Y device access
        # The "default" device tells PulseAudio to use system default input
        command.extend(
            [
                "-f",
                AUDIO_INPUT_FORMAT,  # PulseAudio input (more reliable)
                "-ac",
                str(AUDIO_CHANNELS),  # Audio channels (1=mono, 2=stereo)
                "-ar",
                str(AUDIO_SAMPLE_RATE),  # Sample rate (44100 Hz)
                "-thread_queue_size",
                str(THREAD_QUEUE_SIZE),  # Audio buffer (same as video)
                "-i",
                AUDIO_INPUT_DEVICE,  # "default" = PulseAudio default source
            ],
        )

    # Output options
    command.extend(
        [
            # Video encoding
            "-c:v",
            VIDEO_CODEC,  # H264 video codec
            "-preset",
            VIDEO_PRESET,  # Encoding speed
            "-crf",
            str(VIDEO_CRF),  # Quality level
            "-pix_fmt",
            "yuv420p",  # Pixel format (compatible)
        ],
    )

    # Add audio encoding if enabled
    if CAPTURE_AUDIO:
        command.extend(
            [
                "-c:a",
                AUDIO_CODEC,  # AAC audio codec
                "-b:a",
                AUDIO_BITRATE,  # Audio bitrate (128k)
            ],
        )

    # Final output options
    command.extend(
        [
            "-movflags",
            # WHY frag_keyframe+empty_moov: Ensures valid MP4 even if
            # interrupted. Context: We stop FFmpeg with SIGTERM (manual stop),
            # not natural completion. Standard movflags require FFmpeg to
            # finish normally to finalize the moov atom (MP4 metadata). If
            # interrupted, file is corrupted ("moov atom not found").
            # These flags create fragmented MP4:
            #   - empty_moov: Write moov atom at start (empty placeholder)
            #   - frag_keyframe: Create fragments at each keyframe
            # Result: File is always valid, even if SIGTERM interrupts
            # recording. Tradeoff: Slightly larger file size (~2-5%) vs
            # guaranteed validity
            # Alternative: +faststart requires natural completion (not
            # suitable)
            "+frag_keyframe+empty_moov",
            # Logging
            "-loglevel",
            FFMPEG_LOG_LEVEL,
            # Output file (overwrite if exists)
            "-y",
            output_file,
        ],
    )

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
