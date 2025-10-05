"""
Storage Constants

Centralized configuration for the storage module.
Following the same pattern as hardware/constants.py.

All magic numbers, paths, and configuration values live here.
"""

from enum import Enum
from pathlib import Path

# =============================================================================
# DIRECTORY CONFIGURATION
# =============================================================================
# Base storage directory (configurable via YAML)
DEFAULT_STORAGE_BASE = Path("/home/pi/videos")

# Subdirectory names
DIR_PENDING = "pending"  # New recordings awaiting upload
DIR_UPLOADED = "uploaded"  # Successfully uploaded videos (kept for backup)
DIR_FAILED = "failed"  # Failed uploads (retry queue)
DIR_CORRUPTED = "corrupted"  # Videos that failed validation

# =============================================================================
# FILE NAMING
# =============================================================================
# Video filename pattern: recording_YYYY-MM-DD_HHMMSS.mp4
VIDEO_FILENAME_PREFIX = "recording"
VIDEO_FILENAME_EXTENSION = ".mp4"
VIDEO_FILENAME_PATTERN = (
    f"{VIDEO_FILENAME_PREFIX}_%Y-%m-%d_%H%M%S{VIDEO_FILENAME_EXTENSION}"
)

# Metadata database filename
METADATA_DB_NAME = "video_metadata.db"

# =============================================================================
# STORAGE LIMITS
# =============================================================================
# Maximum number of videos to keep in uploaded directory
MAX_UPLOADED_VIDEOS = 30

# Retention period for uploaded videos (in days)
UPLOADED_RETENTION_DAYS = 7

# Minimum free disk space required to start recording (in bytes)
# 5 GB = 5 * 1024 * 1024 * 1024
MIN_FREE_SPACE_BYTES = 5 * 1024 * 1024 * 1024

# Warning threshold (when to warn about low space)
# 10 GB
LOW_SPACE_WARNING_BYTES = 10 * 1024 * 1024 * 1024

# =============================================================================
# UPLOAD RETRY CONFIGURATION
# =============================================================================
# Maximum number of upload retry attempts
MAX_UPLOAD_RETRIES = 2

# Delay between retry attempts (in seconds)
# 5 minutes = 300 seconds
RETRY_DELAY_SECONDS = 300

# =============================================================================
# FILE VALIDATION
# =============================================================================
# Minimum valid video file size (in bytes)
# 1 MB - anything smaller is probably corrupted
MIN_VIDEO_SIZE_BYTES = 1 * 1024 * 1024

# Timeout for video validation (in seconds)
VALIDATION_TIMEOUT_SECONDS = 10

# =============================================================================
# CLEANUP CONFIGURATION
# =============================================================================
# How often to run cleanup task (in seconds)
# 1 hour = 3600 seconds
CLEANUP_INTERVAL_SECONDS = 3600

# Batch size for cleanup operations (files per batch)
CLEANUP_BATCH_SIZE = 10

# =============================================================================
# ENUMS
# =============================================================================


class UploadStatus(Enum):
    """Video upload status states"""

    PENDING = "pending"  # Waiting for upload
    IN_PROGRESS = "in_progress"  # Currently uploading
    COMPLETED = "completed"  # Successfully uploaded
    FAILED = "failed"  # Upload failed (in retry queue)
    CORRUPTED = "corrupted"  # File validation failed


class StorageState(Enum):
    """Overall storage system states"""

    READY = "ready"  # Normal operation
    LOW_SPACE = "low_space"  # Space below warning threshold
    DISK_FULL = "disk_full"  # Space below minimum threshold
    ERROR = "error"  # Storage system error


class VideoQuality(Enum):
    """Video quality validation results"""

    VALID = "valid"  # File is good
    CORRUPTED = "corrupted"  # File is corrupted/unreadable
    TOO_SMALL = "too_small"  # File size too small
    INVALID_FORMAT = "invalid_format"  # Not a valid video format


# =============================================================================
# ERROR MESSAGES
# =============================================================================

ERROR_DISK_FULL = "Insufficient disk space for recording"
ERROR_DIRECTORY_NOT_FOUND = "Storage directory not found"
ERROR_PERMISSION_DENIED = "Permission denied accessing storage"
ERROR_VIDEO_CORRUPTED = "Video file is corrupted"
ERROR_VALIDATION_FAILED = "Video validation failed"
ERROR_METADATA_ERROR = "Metadata database error"

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"
