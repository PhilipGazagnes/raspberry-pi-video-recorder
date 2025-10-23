"""
Space Manager

Monitors disk space and enforces storage limits.
Single responsibility: Disk space management only.
"""

import logging
import shutil
from pathlib import Path
from typing import Optional

import config.settings as settings
from storage.constants import StorageState
from storage.interfaces.storage_interface import StorageError


class SpaceManager:
    """
    Manages disk space monitoring and limits.

    Responsibilities:
    - Check available disk space
    - Determine if recording can proceed
    - Calculate storage statistics
    - Monitor space warnings
    """

    def __init__(self, storage_base: Path):
        """
        Initialize space manager.

        Args:
            storage_base: Base storage directory

        Configuration loaded from config.settings
        """
        self.logger = logging.getLogger(__name__)
        self.storage_base = Path(storage_base)

        self.logger.info(f"Space manager initialized (path: {self.storage_base})")

    def get_disk_usage(self) -> tuple[int, int, int]:
        """
        Get disk usage statistics.

        Returns:
            Tuple of (total_bytes, used_bytes, free_bytes)

        Raises:
            StorageError: If unable to get disk stats
        """
        try:
            usage = shutil.disk_usage(self.storage_base)
            return usage.total, usage.used, usage.free

        except OSError as e:
            raise StorageError(f"Failed to get disk usage: {e}") from e

    def get_free_space(self) -> int:
        """
        Get free disk space in bytes.

        Returns:
            Free space in bytes
        """
        _, _, free = self.get_disk_usage()
        return free

    def get_free_space_gb(self) -> float:
        """
        Get free disk space in gigabytes.

        Returns:
            Free space in GB
        """
        return self.get_free_space() / (1024**3)

    def check_space_available(self, required_bytes: Optional[int] = None) -> bool:
        """
        Check if enough disk space is available.

        Args:
            required_bytes: Specific requirement (default: from settings)

        Returns:
            True if enough space available
        """
        if required_bytes is None:
            required_bytes = settings.MIN_FREE_SPACE_BYTES

        free_space = self.get_free_space()

        is_available = free_space >= required_bytes

        if not is_available:
            self.logger.warning(
                f"Insufficient disk space: {free_space / (1024**3):.2f} GB free, "
                f"need {required_bytes / (1024**3):.2f} GB",
            )

        return is_available

    def get_storage_state(self) -> StorageState:
        """
        Determine current storage state.

        Returns:
            StorageState enum (READY/LOW_SPACE/DISK_FULL)
        """
        try:
            free_space = self.get_free_space()

            if free_space < settings.MIN_FREE_SPACE_BYTES:
                return StorageState.DISK_FULL
            if free_space < settings.LOW_SPACE_WARNING_BYTES:
                return StorageState.LOW_SPACE
            return StorageState.READY

        except StorageError:
            return StorageState.ERROR

    def is_low_space(self) -> bool:
        """
        Check if space is below warning threshold.

        Returns:
            True if space is low (but still usable)
        """
        return self.get_storage_state() == StorageState.LOW_SPACE

    def is_disk_full(self) -> bool:
        """
        Check if disk is too full for recording.

        Returns:
            True if below minimum threshold
        """
        return self.get_storage_state() == StorageState.DISK_FULL

    def calculate_video_storage_size(self, directory_path: Path) -> int:
        """
        Calculate total size of video files in directory.

        Args:
            directory_path: Directory to analyze

        Returns:
            Total size in bytes
        """
        try:
            total_size = 0
            for file_path in directory_path.rglob("*.mp4"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size

        except OSError as e:
            self.logger.warning(f"Error calculating directory size: {e}")
            return 0

    def estimate_recording_space(
        self,
        duration_seconds: int,
        bitrate_mbps: float = 5.0,
    ) -> int:
        """
        Estimate disk space needed for recording.

        Args:
            duration_seconds: Recording duration
            bitrate_mbps: Video bitrate in Mbps (default: 5.0 for 1080p)

        Returns:
            Estimated size in bytes

        Example:
            # 10 minute recording at 5 Mbps
            size = space_manager.estimate_recording_space(600, 5.0)
            # Returns: ~375 MB
        """
        # Bitrate in bits per second
        bitrate_bps = bitrate_mbps * 1_000_000

        # Total bits = bitrate * duration
        total_bits = bitrate_bps * duration_seconds

        # Convert to bytes (8 bits per byte)
        total_bytes = total_bits / 8

        # Add 10% overhead for container format
        total_bytes *= 1.1

        return int(total_bytes)

    def can_record(
        self,
        estimated_size_bytes: Optional[int] = None,
    ) -> tuple[bool, str]:
        """
        Check if recording can proceed.

        Args:
            estimated_size_bytes: Expected recording size (optional)

        Returns:
            Tuple of (can_record, reason)

        Example:
            can_record, reason = space_manager.can_record(400_000_000)
            if not can_record:
                print(f"Cannot record: {reason}")
        """
        state = self.get_storage_state()

        if state == StorageState.ERROR:
            return False, "Storage system error"

        if state == StorageState.DISK_FULL:
            free_gb = self.get_free_space_gb()
            min_gb = settings.MIN_FREE_SPACE_BYTES / (1024**3)
            return False, f"Disk full: {free_gb:.2f} GB free (need {min_gb:.1f} GB)"

        # If estimated size provided, check against that too
        if estimated_size_bytes:
            free_space = self.get_free_space()
            if free_space < estimated_size_bytes:
                needed_gb = estimated_size_bytes / (1024**3)
                free_gb = free_space / (1024**3)
                return (
                    False,
                    f"Insufficient space for recording: {free_gb:.2f} GB free, need {needed_gb:.2f} GB",
                )

        # Space is available
        if state == StorageState.LOW_SPACE:
            return True, "Warning: disk space low"

        return True, "Sufficient space available"

    def get_space_stats(self) -> dict:
        """
        Get detailed space statistics.

        Returns:
            Dictionary with space information
        """
        total, used, free = self.get_disk_usage()

        return {
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "total_gb": total / (1024**3),
            "used_gb": used / (1024**3),
            "free_gb": free / (1024**3),
            "usage_percent": (used / total * 100) if total > 0 else 0,
            "state": self.get_storage_state().value,
            "min_required_gb": settings.MIN_FREE_SPACE_BYTES / (1024**3),
            "warning_threshold_gb": settings.LOW_SPACE_WARNING_BYTES / (1024**3),
        }

    def log_space_status(self) -> None:
        """Log current disk space status"""
        stats = self.get_space_stats()
        state = stats["state"]
        free_gb = stats["free_gb"]
        usage_pct = stats["usage_percent"]

        if state == "disk_full":
            self.logger.error(
                f"DISK FULL: {free_gb:.2f} GB free ({usage_pct:.1f}% used)",
            )
        elif state == "low_space":
            self.logger.warning(
                f"LOW SPACE: {free_gb:.2f} GB free ({usage_pct:.1f}% used)",
            )
        else:
            self.logger.info(
                f"Space OK: {free_gb:.2f} GB free ({usage_pct:.1f}% used)",
            )
