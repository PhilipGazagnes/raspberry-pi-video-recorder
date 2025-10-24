"""
Storage Module Enums

Type definitions for the storage module.
Configuration values have been consolidated into config/settings.py
following the "ALL config in config/settings.py" principle.

This module now contains only Enum types that define the type system
for storage operations.
"""

from enum import Enum

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
