#!/usr/bin/env python3
"""
Cleanup Orphaned Database Entries

Scans the video metadata database and removes entries for files that no longer
exist on disk. Useful after manually deleting video files from temp_videos/.

Usage:
    python scripts/cleanup_orphaned_db_entries.py          # Dry run
    python scripts/cleanup_orphaned_db_entries.py --apply  # Actually delete

Why this is needed:
- When you manually delete files from temp_videos/, the DB entries remain
- Orphaned entries can cause upload errors and incorrect storage stats
- This script syncs the DB with actual filesystem state
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage import create_storage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def cleanup_orphaned_entries(dry_run: bool = True) -> dict:
    """
    Find and optionally delete orphaned database entries.

    Args:
        dry_run: If True, only report what would be deleted

    Returns:
        Statistics dict with counts
    """
    logger.info("Starting orphaned entry cleanup...")
    logger.info(f"Mode: {'DRY RUN (no changes)' if dry_run else 'APPLY (will delete)'}")

    # Initialize storage
    storage = create_storage()

    # Get all videos from database
    # list_videos() with no args returns all videos regardless of status
    all_videos = storage.list_videos()
    logger.info(f"Found {len(all_videos)} total videos in database")

    # Check which files exist
    orphaned = []
    existing = []

    for video in all_videos:
        if video.exists:
            existing.append(video)
        else:
            orphaned.append(video)
            logger.warning(
                f"Orphaned entry: {video.filename} "
                f"(status: {video.status.value}, "
                f"path: {video.filepath})",
            )

    logger.info(f"Found {len(existing)} existing files")
    logger.info(f"Found {len(orphaned)} orphaned entries")

    # Delete orphaned entries if not dry run
    deleted_count = 0
    if orphaned and not dry_run:
        logger.info("Deleting orphaned entries...")
        for video in orphaned:
            try:
                # Delete from database only (file already gone)
                # remove_file=False because the file doesn't exist anymore
                storage.delete_video(video, remove_file=False)
                deleted_count += 1
                logger.info(f"✓ Deleted DB entry: {video.filename}")
            except Exception as e:
                logger.error(f"✗ Failed to delete {video.filename}: {e}")

    # Summary
    stats = {
        "total_videos": len(all_videos),
        "existing_files": len(existing),
        "orphaned_entries": len(orphaned),
        "deleted_entries": deleted_count,
        "dry_run": dry_run,
    }

    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total DB entries:     {stats['total_videos']}")
    logger.info(f"Existing files:       {stats['existing_files']}")
    logger.info(f"Orphaned entries:     {stats['orphaned_entries']}")
    if dry_run:
        logger.info(
            f"Would delete:         {stats['orphaned_entries']} "
            "(use --apply to delete)",
        )
    else:
        logger.info(f"Deleted entries:      {stats['deleted_entries']}")
    logger.info("=" * 60)

    return stats


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Clean up orphaned database entries for deleted video files",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete orphaned entries (default is dry run)",
    )
    args = parser.parse_args()

    try:
        stats = cleanup_orphaned_entries(dry_run=not args.apply)

        if stats["orphaned_entries"] > 0 and args.apply:
            logger.info(
                f"✅ Cleanup complete: Removed {stats['deleted_entries']} "
                "orphaned entries",
            )
        elif stats["orphaned_entries"] > 0:
            logger.info(
                "💡 Run with --apply to actually delete these orphaned entries",
            )
        else:
            logger.info("✅ No orphaned entries found - database is clean!")

    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
