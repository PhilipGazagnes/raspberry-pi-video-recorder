"""
Central Configuration File

ALL configuration values live here. This is the single source of truth.

Guidelines:
- Secrets (API keys, credentials) should be in .env, NOT here
- Import these settings in modules: from config.settings import GPIO_BUTTON_PIN
- Keep values generic and domain-agnostic
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# HARDWARE CONFIGURATION
# =============================================================================

# GPIO Pin Assignments
GPIO_BUTTON_PIN = 18  # Hardware PWM pin (physical pin 12)
GPIO_LED_GREEN = 13  # Hardware PWM pin (physical pin 33)
GPIO_LED_ORANGE = 12  # Hardware PWM pin (physical pin 32)
GPIO_LED_RED = 19  # Hardware PWM pin (physical pin 35)
GPIO_LED_WHITE = 27  # Status LED for network connectivity (dimmed)
GPIO_LED_BLUE = 17  # Status LED for upload activity (dimmed, blinking)

# Button Configuration
BUTTON_LONG_PRESS_DURATION = 1.0  # seconds - hold duration for long press

# =============================================================================
# LED ANIMATION CONFIGURATION
# =============================================================================
# Pattern Format: 12 steps separated by "-"
# Step codes: G=Green, O=Orange, R=Red, x=Blank (or _ for blank)
# Multi-LED steps: GO=Green+Orange, GOR=All three, etc.
#
# Each pattern has 3-4 parameters:
# - PATTERN: 12-step sequence string defining LED states
# - STEP_DURATION: Seconds per step (12 steps = one full cycle)
# - PAUSE_DURATION: Seconds of blank gap between cycles (0 = continuous)
# - REPEAT_COUNT: Number of cycles before stopping (omit for infinite loop)
#
# Timing calculation: total_cycle_time = (12 * STEP_DURATION) + PAUSE_DURATION
#
# Examples:
#   "G-x-G-x-G-x-G-x-G-x-G-x"     → Simple blink (6 on, 6 off)
#   "GO-x-GO-x-GO-x-GO-x-GO-x-GO-x" → Green+Orange alternating blink
#   "G-O-R-GOR-G-O-R-GOR-x-x-x-x" → Sequence with multi-LED step
#   "GGG-x-x-x-GGG-x-x-x-x-x-x-x" → Double pulse pattern

# Ready State - Green solid (handled separately, no pattern needed)
# This is a static state, not animated

# Recording - Normal green blink (0.5s on, 0.5s off = 1.0s cycle)
LED_RECORDING_PATTERN = "G-x-G-x-G-x-G-x-G-x-G-x"
LED_RECORDING_STEP_DURATION = 0.083  # 12 * 0.083 = ~1.0s per cycle
LED_RECORDING_PAUSE_DURATION = 0.0  # Continuous, no gap between cycles

# Recording Started - 3 quick green flashes when recording begins
LED_RECORDING_STARTED_PATTERN = "GGG-x-x-x-GGG-x-x-x-x-x-x-x"
LED_RECORDING_STARTED_STEP_DURATION = 0.05  # 12 * 0.05 = 0.6s per cycle
LED_RECORDING_STARTED_PAUSE_DURATION = 0.2  # 0.2s gap between flashes
LED_RECORDING_STARTED_REPEAT_COUNT = 3  # Flash 3 times then stop

# Warning Level 1 (WARNING_TIME_1) - Green+Orange double blink
LED_RECORDING_WARN1_PATTERN = "GO-x-GO-x-x-x-GO-x-GO-x-x-x"
LED_RECORDING_WARN1_STEP_DURATION = 0.083  # 12 * 0.083 = ~1.0s
LED_RECORDING_WARN1_PAUSE_DURATION = 0.0  # Continuous

# Warning Level 2 (WARNING_TIME_2) - All colors rapid sequence
LED_RECORDING_WARN2_PATTERN = "G-O-R-GOR-G-O-R-GOR-G-O-R-GOR"
LED_RECORDING_WARN2_STEP_DURATION = 0.042  # 12 * 0.042 = ~0.5s per cycle
LED_RECORDING_WARN2_PAUSE_DURATION = 0.5  # 0.5s blank gap between sequences

# Warning Level 3 (WARNING_TIME_3) - Fast all-LED flash
LED_RECORDING_WARN3_PATTERN = "GOR-x-GOR-x-GOR-x-GOR-x-GOR-x-GOR-x"
LED_RECORDING_WARN3_STEP_DURATION = 0.042  # 12 * 0.042 = ~0.5s
LED_RECORDING_WARN3_PAUSE_DURATION = 0.0  # Continuous rapid flash

# Extension Added - 5 quick green pulses to confirm time added
LED_EXTENSION_ADDED_PATTERN = "GGG-x-x-x-GGG-x-x-x-x-x-x-x"
LED_EXTENSION_ADDED_STEP_DURATION = 0.05  # 12 * 0.05 = 0.6s per cycle
LED_EXTENSION_ADDED_PAUSE_DURATION = 0.15  # 0.15s between pulses
LED_EXTENSION_ADDED_REPEAT_COUNT = 5  # 5 pulses then restore previous pattern

# Error - Fast red flash to grab attention
LED_ERROR_PATTERN = "R-x-R-x-R-x-R-x-R-x-R-x"
LED_ERROR_STEP_DURATION = 0.017  # 12 * 0.017 = ~0.2s per cycle (very fast)
LED_ERROR_PAUSE_DURATION = 0.0  # Continuous rapid flash
LED_ERROR_DURATION = 2.0  # Total duration to flash error before restoring

# Processing/Uploading - Orange solid (handled separately, no pattern needed)
# This is a static state, not animated

# Upload Activity (Blue LED) - Simple blink while uploading
LED_UPLOAD_BLINK_PATTERN = "x-x-x-x-x-x-x-x-x-x-x-x"  # Will use simple on/off
LED_UPLOAD_BLINK_INTERVAL = 0.5  # Seconds (on/off each 0.5s = 1.0s cycle)

# Audio/TTS Configuration
TTS_RATE = 150  # Words per minute
TTS_VOLUME = 0.8  # 0.0 to 1.0
SPEAKER_DEVICE = "hw:1,0"  # USB speaker device

# Audio Input Configuration (for recording)
# Using PulseAudio default source (camera microphone)
# "default" tells PulseAudio to use the default input device
# which is the camera's mono microphone
AUDIO_INPUT_DEVICE = "default"  # PulseAudio default source
AUDIO_INPUT_FORMAT = "pulse"  # Use PulseAudio (not raw ALSA)
AUDIO_CHANNELS = 1  # 1 = mono, 2 = stereo (camera is mono)
AUDIO_SAMPLE_RATE = 44100  # Hz - CD quality
AUDIO_CODEC = "aac"  # AAC audio codec (widely compatible)
AUDIO_BITRATE = "128k"  # 128 kbps - good quality for speech/ambient

# =============================================================================
# RECORDING CONFIGURATION
# =============================================================================

# Recording Durations (in seconds)
DEFAULT_RECORDING_DURATION = 600  # (10 minute)
EXTENSION_DURATION = 300  # (5 minute)
MAX_RECORDING_DURATION = 1500  # (25 minutes)

# Progressive Warning System (seconds before end)
# Multiple warning levels provide escalating visual feedback as time runs out
# Set to 0 to disable a warning level
WARNING_TIME_1 = 120  # Level 1: 2 minutes
WARNING_TIME_2 = 60  # Level 2: 1 minute
WARNING_TIME_3 = 30  # Level 3: 30 seconds

# Legacy: Single warning threshold (kept for backward compatibility)
# If you only want one warning, set WARNING_TIME_1 and WARNING_TIME_2 to 0
WARNING_TIME = WARNING_TIME_2  # Default to final warning level

# Network Connectivity Monitoring
NETWORK_CHECK_INTERVAL = 30  # Check internet every 30 seconds (configurable)
NETWORK_CHECK_TIMEOUT = 3  # Timeout for connectivity check (seconds)
NETWORK_CHECK_HOST = "8.8.8.8"  # Google DNS - reliable external host
NETWORK_CHECK_PORT = 53  # DNS port

# Video Settings
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 30
VIDEO_CODEC = "libx264"
VIDEO_PRESET = "ultrafast"  # FFmpeg encoding preset
VIDEO_CRF = 23  # Constant Rate Factor (quality)
VIDEO_FORMAT = "mp4"

# Camera Configuration
DEFAULT_CAMERA_DEVICE = "/dev/video0"
CAMERA_WARMUP_TIME = 1.0  # seconds

# =============================================================================
# STORAGE CONFIGURATION
# =============================================================================

# Storage Paths
STORAGE_BASE_PATH = Path("./temp_videos")  # /home/pi/videos

# Directory Names (subdirectories under STORAGE_BASE_PATH)
DIR_PENDING = "pending"
DIR_UPLOADED = "uploaded"
DIR_FAILED = "failed"
DIR_CORRUPTED = "corrupted"

# Video File Naming
VIDEO_FILENAME_PREFIX = "recording"
VIDEO_FILENAME_EXTENSION = ".mp4"
VIDEO_FILENAME_PATTERN = (
    f"{VIDEO_FILENAME_PREFIX}_%Y-%m-%d_%H%M%S{VIDEO_FILENAME_EXTENSION}"
)
METADATA_DB_NAME = "video_metadata.db"

# Space Management (in bytes)
MIN_FREE_SPACE_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB
LOW_SPACE_WARNING_BYTES = 10 * 1024 * 1024 * 1024  # 10 GB

# Video Retention
MAX_UPLOADED_VIDEOS = 20  # Maximum videos in uploaded directory
UPLOADED_RETENTION_DAYS = 7  # Days to keep uploaded videos

# Upload Retry Configuration
MAX_UPLOAD_RETRIES = 2
RETRY_DELAY_SECONDS = 300  # 5 minutes

# File Validation
MIN_VIDEO_SIZE_BYTES = 1 * 1024 * 1024  # 1 MB minimum
VALIDATION_TIMEOUT_SECONDS = 10  # Timeout for video validation
ENABLE_FFMPEG_VALIDATION = True  # Use FFmpeg for video validation

# Cleanup Configuration
CLEANUP_INTERVAL_SECONDS = 3600  # 1 hour
CLEANUP_BATCH_SIZE = 10  # Files per batch during cleanup
AUTO_CLEANUP_ENABLED = True

# =============================================================================
# MONITORING CONFIGURATION
# =============================================================================

# Heartbeat Configuration
HEARTBEAT_INTERVAL = float(os.getenv("HEARTBEAT_INTERVAL", "1.0"))  # seconds
# /tmp is intentional - standard location for watchdog monitoring
HEARTBEAT_FILE = os.getenv(
    "HEARTBEAT_FILE",
    "/tmp/recorder_heartbeat.json",  # noqa: S108
)
HEARTBEAT_TIMEOUT = int(os.getenv("HEARTBEAT_TIMEOUT", "30"))  # seconds

# Remote Control Configuration
# File-based control for triggering actions via SSH/scripts
# Commands: START, STOP, EXTEND, STATUS
CONTROL_FILE = os.getenv(
    "CONTROL_FILE",
    "/tmp/recorder_control.cmd",  # noqa: S108
)

# Restart Counter (persistent across service restarts)
RESTART_COUNTER_FILE = os.getenv(
    "RESTART_COUNTER_FILE",
    "/tmp/recorder_restart_count.txt",  # noqa: S108
)

# Watchdog Configuration
WATCHDOG_CHECK_INTERVAL = int(os.getenv("WATCHDOG_CHECK_INTERVAL", "10"))  # seconds
WATCHDOG_MAX_RESTART_ATTEMPTS = int(
    os.getenv("WATCHDOG_MAX_RESTART_ATTEMPTS", "3"),
)
WATCHDOG_RESTART_WINDOW = int(
    os.getenv("WATCHDOG_RESTART_WINDOW", "600"),
)  # seconds

# Metrics Configuration
METRICS_PORT = int(os.getenv("METRICS_PORT", "9101"))
NODE_EXPORTER_PORT = int(os.getenv("NODE_EXPORTER_PORT", "9100"))

# Logging Configuration
LOG_DIR = "/var/log/recorder"
LOG_SERVICE_FILE = "service.log"
LOG_WATCHDOG_FILE = "watchdog.log"
LOG_REBOOT_TRIGGER_FILE = "reboot_trigger.log"

# =============================================================================
# UPLOAD CONFIGURATION
# =============================================================================

# Video Metadata (GENERIC - customize for your use case)
SESSION_TITLE_PREFIX = "Video Session"  # Change to match your domain
DEFAULT_VIDEO_TAGS = ["recording", "session"]  # Customize tags
DEFAULT_PRIVACY_STATUS = "unlisted"  # public, private, or unlisted

# YouTube Category
YOUTUBE_CATEGORY_ID = "17"  # 17 = Sports (change as needed)

# Upload Settings
UPLOAD_CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB chunks
UPLOAD_TIMEOUT = 600  # 10 minutes
HTTP_TIMEOUT = 30  # seconds

# =============================================================================
# SECRETS (loaded from .env)
# =============================================================================
# IMPORTANT: These should NEVER be committed to version control!
# Create a .env file in the project root with these values

# YouTube OAuth Configuration (file-based)
# These point to credential files, not inline secrets
YOUTUBE_CLIENT_SECRET_PATH = os.getenv(
    "YOUTUBE_CLIENT_SECRET_PATH",
    "credentials/client_secret.json",
)
YOUTUBE_TOKEN_PATH = os.getenv("YOUTUBE_TOKEN_PATH", "credentials/token.json")
YOUTUBE_PLAYLIST_ID = os.getenv("YOUTUBE_PLAYLIST_ID", "")  # Optional playlist ID
