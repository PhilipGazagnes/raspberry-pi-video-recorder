"""
Storage Module

Video storage management system for the boxing club recording project.

Architecture mirrors the hardware module:
- interfaces/: Abstract base classes (contracts)
- implementations/: Concrete implementations (real and mock)
- controllers/: High-level coordination
- managers/: Specialized domain logic
- models/: Data structures
- utils/: Shared utilities
"""

# ============================================================================
# storage/__init__.py - Main Package Exports
# ============================================================================

from storage.constants import (
    DIR_CORRUPTED,
    DIR_FAILED,
    DIR_PENDING,
    DIR_UPLOADED,
    StorageState,
    UploadStatus,
    VideoQuality,
)
from storage.controllers.storage_controller import StorageController
from storage.factory import StorageFactory, create_storage
from storage.interfaces.storage_interface import StorageError, StorageInterface
from storage.models.video_file import StorageStats, VideoFile

# Public API - what users import
__all__ = [
    "DIR_CORRUPTED",
    "DIR_FAILED",
    "DIR_PENDING",
    "DIR_UPLOADED",
    # Main controller (primary API)
    "StorageController",
    "StorageError",
    # Factory for creating storage
    "StorageFactory",
    # Interfaces
    "StorageInterface",
    "StorageState",
    "StorageStats",
    # Enums and constants
    "UploadStatus",
    # Models
    "VideoFile",
    "VideoQuality",
    "create_storage",
]


# ============================================================================
# storage/models/__init__.py
# ============================================================================
"""
from storage.models.video_file import StorageStats, VideoFile

__all__ = [
    "VideoFile",
    "StorageStats",
]
"""


# ============================================================================
# storage/interfaces/__init__.py
# ============================================================================
"""
from storage.interfaces.storage_interface import StorageError, StorageInterface

__all__ = [
    "StorageInterface",
    "StorageError",
]
"""


# ============================================================================
# storage/implementations/__init__.py
# ============================================================================
"""
from storage.implementations.local_storage import LocalStorage
from storage.implementations.mock_storage import MockStorage

__all__ = [
    "LocalStorage",
    "MockStorage",
]
"""


# ============================================================================
# storage/controllers/__init__.py
# ============================================================================
"""
from storage.controllers.storage_controller import StorageController

__all__ = [
    "StorageController",
]
"""


# ============================================================================
# storage/managers/__init__.py
# ============================================================================
"""
from storage.managers.cleanup_manager import CleanupManager
from storage.managers.file_manager import FileManager
from storage.managers.metadata_manager import MetadataManager
from storage.managers.space_manager import SpaceManager

__all__ = [
    "FileManager",
    "MetadataManager",
    "SpaceManager",
    "CleanupManager",
]
"""


# ============================================================================
# storage/utils/__init__.py
# ============================================================================
"""
from storage.utils.path_utils import (
    calculate_directory_size,
    ensure_directory,
    format_duration,
    format_size,
    get_file_extension,
    get_relative_path,
    is_path_writable,
    is_video_file,
    safe_filename,
    validate_path,
)
from storage.utils.validation_utils import (
    get_video_duration,
    get_video_info,
    quick_validate,
    validate_video_file,
    validate_with_ffmpeg,
)

__all__ = [
    # Path utilities
    "validate_path",
    "ensure_directory",
    "safe_filename",
    "get_file_extension",
    "is_video_file",
    "get_relative_path",
    "format_size",
    "format_duration",
    "calculate_directory_size",
    "is_path_writable",

    # Validation utilities
    "validate_video_file",
    "validate_with_ffmpeg",
    "get_video_duration",
    "get_video_info",
    "quick_validate",
]
"""
