"""
Upload Constants

Centralized configuration for YouTube upload module.
Following the same pattern as hardware/constants.py for consistency.
"""

from enum import Enum

# =============================================================================
# YOUTUBE API CONFIGURATION
# =============================================================================

# OAuth 2.0 scopes required for YouTube operations
# https://developers.google.com/youtube/v3/guides/authentication
YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

# YouTube API service details
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# =============================================================================
# UPLOAD CONFIGURATION
# =============================================================================

# Chunk size for resumable uploads (in bytes)
# 10 MB is a good balance: not too small (many requests), not too large (memory)
# YouTube requires multiples of 256 KB
UPLOAD_CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB

# Maximum time to wait for upload completion (seconds)
# 10 minutes should be enough for 750 MB video on decent connection
UPLOAD_TIMEOUT = 600  # 10 minutes

# HTTP request timeout (seconds)
# Individual API calls should complete quickly
HTTP_TIMEOUT = 30

# =============================================================================
# VIDEO METADATA CONFIGURATION
# =============================================================================

# Default video privacy status
# Options: "public", "private", "unlisted"
DEFAULT_PRIVACY_STATUS = "unlisted"

# Video category ID for Sports
# YouTube category IDs: https://developers.google.com/youtube/v3/docs/videoCategories
YOUTUBE_CATEGORY_SPORTS = "17"

# Default video tags
DEFAULT_VIDEO_TAGS = ["boxing", "training", "practice"]

# Title format: "Boxing Session YYYY-MM-DD HH:MM:SS"
VIDEO_TITLE_PREFIX = "Boxing Session"

# =============================================================================
# UPLOAD STATUS
# =============================================================================


class UploadStatus(Enum):
    """Upload operation status codes"""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    AUTH_ERROR = "auth_error"
    NETWORK_ERROR = "network_error"
    INVALID_FILE = "invalid_file"
    QUOTA_EXCEEDED = "quota_exceeded"


# =============================================================================
# FILE VALIDATION
# =============================================================================

# Supported video formats
SUPPORTED_VIDEO_FORMATS = [".mp4", ".avi", ".mov", ".mkv"]

# Maximum file size (bytes) - YouTube limit is 256 GB
# Setting to 2 GB for practical limit (longer videos unlikely in your use case)
MAX_VIDEO_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB

# Minimum file size (bytes) - sanity check for corrupted files
MIN_VIDEO_FILE_SIZE = 1 * 1024 * 1024  # 1 MB

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_ERROR = "ERROR"
