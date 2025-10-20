"""
Interfaces Package

Abstract interfaces for upload implementations.
"""

from upload.interfaces.uploader_interface import (
    UploaderError,
    UploaderInterface,
    UploadResult,
)

__all__ = [
    "UploaderInterface",
    "UploadResult",
    "UploaderError",
]
