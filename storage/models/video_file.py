"""
Video File Models

Data classes representing video files and their metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from storage.constants import UploadStatus, VideoQuality


@dataclass
class VideoFile:
    """
    Represents a video file and its metadata.

    This is the core data structure for tracking videos throughout their lifecycle:
    pending → in_progress → completed/failed → cleanup
    """

    # File identification
    filename: str  # Just the filename: recording_2025-10-04_143025.mp4
    filepath: Path  # Full path to file

    # Timestamps
    created_at: datetime  # When recording was created
    updated_at: datetime = field(default_factory=datetime.now)  # Last status change

    # Video information
    duration_seconds: Optional[int] = None  # Video length in seconds
    file_size_bytes: Optional[int] = None  # File size in bytes

    # Upload tracking
    status: UploadStatus = UploadStatus.PENDING
    upload_attempts: int = 0  # Number of upload attempts
    last_upload_attempt: Optional[datetime] = None
    upload_error: Optional[str] = None  # Last error message
    youtube_url: Optional[str] = None  # URL after successful upload

    # Validation
    quality: VideoQuality = VideoQuality.VALID
    validation_error: Optional[str] = None

    # Database ID (set after insertion)
    id: Optional[int] = None

    def __post_init__(self):
        """Ensure filepath is a Path object"""
        if not isinstance(self.filepath, Path):
            self.filepath = Path(self.filepath)

    @property
    def exists(self) -> bool:
        """Check if file still exists on disk"""
        return self.filepath.exists()

    @property
    def is_pending(self) -> bool:
        """Check if video is waiting for upload"""
        return self.status == UploadStatus.PENDING

    @property
    def is_completed(self) -> bool:
        """Check if video was successfully uploaded"""
        return self.status == UploadStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if video upload failed"""
        return self.status == UploadStatus.FAILED

    @property
    def is_corrupted(self) -> bool:
        """Check if video is corrupted"""
        return self.status == UploadStatus.CORRUPTED

    @property
    def can_retry(self) -> bool:
        """Check if video can be retried (failed but under retry limit)"""
        from storage.constants import MAX_UPLOAD_RETRIES

        return self.is_failed and self.upload_attempts < MAX_UPLOAD_RETRIES

    @property
    def age_days(self) -> float:
        """Get age of video in days"""
        return (datetime.now() - self.created_at).total_seconds() / 86400

    def mark_upload_started(self) -> None:
        """Mark video as upload in progress"""
        self.status = UploadStatus.IN_PROGRESS
        self.updated_at = datetime.now()

    def mark_upload_success(self, youtube_url: str) -> None:
        """Mark video as successfully uploaded"""
        self.status = UploadStatus.COMPLETED
        self.youtube_url = youtube_url
        self.updated_at = datetime.now()
        self.upload_error = None

    def mark_upload_failed(self, error: str) -> None:
        """Mark video upload as failed"""
        self.status = UploadStatus.FAILED
        self.upload_attempts += 1
        self.last_upload_attempt = datetime.now()
        self.upload_error = error
        self.updated_at = datetime.now()

    def mark_corrupted(self, error: str) -> None:
        """Mark video as corrupted"""
        self.status = UploadStatus.CORRUPTED
        self.quality = VideoQuality.CORRUPTED
        self.validation_error = error
        self.updated_at = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        return {
            "filename": self.filename,
            "filepath": str(self.filepath),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "file_size_bytes": self.file_size_bytes,
            "status": self.status.value,
            "upload_attempts": self.upload_attempts,
            "last_upload_attempt": (
                self.last_upload_attempt.isoformat()
                if self.last_upload_attempt
                else None
            ),
            "upload_error": self.upload_error,
            "youtube_url": self.youtube_url,
            "quality": self.quality.value,
            "validation_error": self.validation_error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VideoFile":
        """Create VideoFile from dictionary (database row)"""
        return cls(
            id=data.get("id"),
            filename=data["filename"],
            filepath=Path(data["filepath"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            duration_seconds=data.get("duration_seconds"),
            file_size_bytes=data.get("file_size_bytes"),
            status=UploadStatus(data["status"]),
            upload_attempts=data.get("upload_attempts", 0),
            last_upload_attempt=(
                datetime.fromisoformat(data["last_upload_attempt"])
                if data.get("last_upload_attempt")
                else None
            ),
            upload_error=data.get("upload_error"),
            youtube_url=data.get("youtube_url"),
            quality=VideoQuality(data.get("quality", "valid")),
            validation_error=data.get("validation_error"),
        )

    def __repr__(self) -> str:
        """Human-readable representation"""
        return (
            f"VideoFile(filename='{self.filename}', "
            f"status={self.status.value}, "
            f"attempts={self.upload_attempts})"
        )


@dataclass
class StorageStats:
    """
    Storage system statistics.

    Used for monitoring and decision-making.
    """

    # Disk space
    total_space_bytes: int
    free_space_bytes: int
    used_space_bytes: int

    # Video counts by status
    pending_count: int = 0
    in_progress_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    corrupted_count: int = 0

    # Total counts
    total_videos: int = 0
    total_size_bytes: int = 0

    @property
    def free_space_gb(self) -> float:
        """Free space in gigabytes"""
        return self.free_space_bytes / (1024**3)

    @property
    def used_space_gb(self) -> float:
        """Used space in gigabytes"""
        return self.used_space_bytes / (1024**3)

    @property
    def total_space_gb(self) -> float:
        """Total space in gigabytes"""
        return self.total_space_bytes / (1024**3)

    @property
    def space_usage_percent(self) -> float:
        """Percentage of space used"""
        if self.total_space_bytes == 0:
            return 0.0
        return (self.used_space_bytes / self.total_space_bytes) * 100

    @property
    def is_low_space(self) -> bool:
        """Check if space is below warning threshold"""
        from storage.constants import LOW_SPACE_WARNING_BYTES

        return self.free_space_bytes < LOW_SPACE_WARNING_BYTES

    @property
    def is_disk_full(self) -> bool:
        """Check if space is below minimum threshold"""
        from storage.constants import MIN_FREE_SPACE_BYTES

        return self.free_space_bytes < MIN_FREE_SPACE_BYTES

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/display"""
        return {
            "free_space_gb": round(self.free_space_gb, 2),
            "used_space_gb": round(self.used_space_gb, 2),
            "total_space_gb": round(self.total_space_gb, 2),
            "space_usage_percent": round(self.space_usage_percent, 2),
            "pending_count": self.pending_count,
            "in_progress_count": self.in_progress_count,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "corrupted_count": self.corrupted_count,
            "total_videos": self.total_videos,
            "is_low_space": self.is_low_space,
            "is_disk_full": self.is_disk_full,
        }

    def __repr__(self) -> str:
        """Human-readable representation"""
        return (
            f"StorageStats(free={self.free_space_gb:.1f}GB, "
            f"usage={self.space_usage_percent:.1f}%, "
            f"videos={self.total_videos})"
        )
