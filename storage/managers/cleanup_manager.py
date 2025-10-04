"""
Cleanup Manager

Manages video cleanup according to retention policies.
Single responsibility: Cleanup operations only.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from storage.constants import DIR_UPLOADED, CLEANUP_BATCH_SIZE
from storage.interfaces.storage_interface import StorageError
from storage.models.video_file import VideoFile


class CleanupManager:
    """
    Manages video cleanup and retention policies.

    Responsibilities:
    - Clean up old uploaded videos
    - Enforce maximum video count
    - Batch cleanup operations
    - Track cleanup statistics
    """

    def __init__(self, config):
        """
        Initialize cleanup manager.

        Args:
            config: StorageConfig object for policies
        """
        self.logger = logging.getLogger(__name__)
        self.config = config

        self.logger.info("Cleanup manager initialized")

    def should_cleanup_video(self, video: VideoFile) -> tuple[bool, str]:
        """
        Determine if video should be cleaned up.

        Args:
            video: VideoFile to check

        Returns:
            Tuple of (should_cleanup, reason)
        """
        # Only clean up completed uploads
        if not video.is_completed:
            return False, "Not completed"

        # Check age
        age_days = video.age_days
        retention_days = self.config.uploaded_retention_days

        if age_days > retention_days:
            return True, f"Age ({age_days:.1f} days) exceeds retention ({retention_days} days)"

        return False, "Within retention period"

    def get_videos_to_cleanup(
        self,
        all_uploaded: List[VideoFile]
    ) -> List[VideoFile]:
        """
        Get list of videos that should be cleaned up.

        Args:
            all_uploaded: All uploaded videos

        Returns:
            List of videos to cleanup (sorted oldest first)
        """
        cleanup_candidates = []

        for video in all_uploaded:
            should_cleanup, reason = self.should_cleanup_video(video)
            if should_cleanup:
                self.logger.debug(f"Cleanup candidate: {video.filename} - {reason}")
                cleanup_candidates.append(video)

        # Sort by age (oldest first)
        cleanup_candidates.sort(key=lambda v: v.created_at)

        return cleanup_candidates

    def enforce_max_count(
        self,
        all_uploaded: List[VideoFile]
    ) -> List[VideoFile]:
        """
        Get videos exceeding maximum count limit.

        Args:
            all_uploaded: All uploaded videos (sorted oldest first)

        Returns:
            List of excess videos to remove
        """
        max_count = self.config.max_uploaded_videos

        if len(all_uploaded) <= max_count:
            return []

        # How many to remove
        excess_count = len(all_uploaded) - max_count

        # Remove oldest videos
        to_remove = all_uploaded[:excess_count]

        self.logger.info(
            f"Enforcing max count: {len(all_uploaded)} videos, "
            f"limit is {max_count}, removing {excess_count} oldest"
        )

        return to_remove

    def plan_cleanup(
        self,
        all_uploaded: List[VideoFile]
    ) -> tuple[List[VideoFile], dict]:
        """
        Plan cleanup operation without executing.

        Args:
            all_uploaded: All uploaded videos

        Returns:
            Tuple of (videos_to_cleanup, statistics)
        """
        # Sort by age (oldest first)
        sorted_videos = sorted(all_uploaded, key=lambda v: v.created_at)

        # Get videos exceeding retention period
        age_based = self.get_videos_to_cleanup(sorted_videos)

        # Get videos exceeding max count
        count_based = self.enforce_max_count(sorted_videos)

        # Combine (use set to avoid duplicates)
        to_cleanup = list(set(age_based + count_based))

        # Sort final list oldest first
        to_cleanup.sort(key=lambda v: v.created_at)

        # Calculate statistics
        if to_cleanup:
            total_size = sum(v.file_size_bytes or 0 for v in to_cleanup)
            oldest = to_cleanup[0].created_at
            newest = to_cleanup[-1].created_at
        else:
            total_size = 0
            oldest = None
            newest = None

        stats = {
            'total_videos': len(all_uploaded),
            'cleanup_count': len(to_cleanup),
            'age_based_count': len(age_based),
            'count_based_count': len(count_based),
            'total_size_bytes': total_size,
            'total_size_gb': total_size / (1024 ** 3),
            'oldest_video': oldest,
            'newest_video': newest,
        }

        return to_cleanup, stats

    def cleanup_videos(
        self,
        videos_to_cleanup: List[VideoFile],
        delete_func: callable,
        batch_size: int = CLEANUP_BATCH_SIZE,
        dry_run: bool = False
    ) -> dict:
        """
        Execute cleanup operation.

        Args:
            videos_to_cleanup: Videos to delete
            delete_func: Function to call for each deletion (video) -> None
            batch_size: Number of videos to delete per batch
            dry_run: If True, only simulate without deleting

        Returns:
            Statistics dictionary
        """
        total = len(videos_to_cleanup)
        deleted = 0
        errors = 0
        total_size = 0

        if dry_run:
            self.logger.info(f"DRY RUN: Would delete {total} videos")
        else:
            self.logger.info(f"Starting cleanup: {total} videos to delete")

        # Process in batches
        for i in range(0, total, batch_size):
            batch = videos_to_cleanup[i:i + batch_size]

            for video in batch:
                try:
                    if not dry_run:
                        # Call the delete function
                        delete_func(video)

                    # Track statistics
                    deleted += 1
                    total_size += video.file_size_bytes or 0

                    self.logger.debug(
                        f"{'Would delete' if dry_run else 'Deleted'}: "
                        f"{video.filename} ({video.age_days:.1f} days old)"
                    )

                except Exception as e:
                    errors += 1
                    self.logger.error(
                        f"Failed to delete {video.filename}: {e}"
                    )

        stats = {
            'total_videos': total,
            'deleted': deleted,
            'errors': errors,
            'total_size_bytes': total_size,
            'total_size_gb': total_size / (1024 ** 3),
            'dry_run': dry_run,
        }

        if dry_run:
            self.logger.info(
                f"DRY RUN complete: Would delete {deleted} videos "
                f"({stats['total_size_gb']:.2f} GB)"
            )
        else:
            self.logger.info(
                f"Cleanup complete: Deleted {deleted}/{total} videos "
                f"({stats['total_size_gb']:.2f} GB), {errors} errors"
            )

        return stats

    def get_cleanup_summary(
        self,
        all_uploaded: List[VideoFile]
    ) -> dict:
        """
        Get summary of what would be cleaned up (without executing).

        Args:
            all_uploaded: All uploaded videos

        Returns:
            Summary dictionary
        """
        to_cleanup, stats = self.plan_cleanup(all_uploaded)

        # Add detailed breakdown
        stats['videos_to_cleanup'] = [
            {
                'filename': v.filename,
                'age_days': round(v.age_days, 1),
                'size_mb': round((v.file_size_bytes or 0) / (1024 ** 2), 2),
                'created_at': v.created_at.isoformat(),
            }
            for v in to_cleanup[:10]  # First 10 only
        ]

        if len(to_cleanup) > 10:
            stats['more_videos'] = len(to_cleanup) - 10

        return stats

    def should_run_auto_cleanup(self, last_cleanup: datetime) -> bool:
        """
        Check if automatic cleanup should run.

        Args:
            last_cleanup: Timestamp of last cleanup

        Returns:
            True if cleanup should run now
        """
        if not self.config.auto_cleanup_enabled:
            return False

        # Check if enough time has passed
        interval = timedelta(seconds=self.config.cleanup_interval_seconds)
        next_cleanup = last_cleanup + interval

        should_run = datetime.now() >= next_cleanup

        if should_run:
            self.logger.debug(
                f"Auto-cleanup triggered "
                f"(last: {last_cleanup}, interval: {interval})"
            )

        return should_run
