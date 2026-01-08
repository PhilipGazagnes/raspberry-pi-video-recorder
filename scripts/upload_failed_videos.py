#!/usr/bin/env python3
"""
Upload Failed Videos - Maintenance Script

Simple, straightforward script to upload all videos from temp_videos/failed/
directory. Does NOT use the database - just scans the directory and uploads
each video file directly.

Perfect for maintenance when you don't trust the database state.

Usage:
    python scripts/upload_failed_videos.py              # Dry run - show what would upload
    python scripts/upload_failed_videos.py --upload     # Actually upload videos
    python scripts/upload_failed_videos.py --upload --move-after  # Move to uploaded/ after success

Safety:
    - Dry run by default (requires --upload to actually upload)
    - Only processes .mp4 files
    - Skips files that don't exist or are too small
    - Continues on errors (one failed upload won't stop the rest)
    - Optional: moves successful uploads to uploaded/ directory
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from upload import UploadController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def extract_timestamp_from_filename(filename: str) -> str:
    """
    Extract timestamp from filename or generate current timestamp.

    Expected format: recording_YYYY-MM-DD_HHMMSS.mp4
    Returns: "YYYY-MM-DD HH:MM:SS"

    If parsing fails, returns current timestamp.
    """
    try:
        # Example: recording_2025-01-05_143025.mp4
        # Extract: 2025-01-05_143025
        name_without_ext = filename.replace(".mp4", "")
        parts = name_without_ext.split("_")

        if len(parts) >= 3:
            date_part = parts[1]  # 2025-01-05
            time_part = parts[2]  # 143025

            # Convert time from HHMMSS to HH:MM:SS
            if len(time_part) == 6:
                hour = time_part[0:2]
                minute = time_part[2:4]
                second = time_part[4:6]
                time_formatted = f"{hour}:{minute}:{second}"

                return f"{date_part} {time_formatted}"
    except Exception as e:
        logger.debug(f"Could not parse timestamp from {filename}: {e}")

    # Fallback: use current time
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_failed_videos(failed_dir: Path) -> list[Path]:
    """
    Get all video files from failed directory.

    Returns:
        List of Path objects for video files
    """
    if not failed_dir.exists():
        logger.error(f"Failed directory does not exist: {failed_dir}")
        return []

    # Find all .mp4 files
    video_files = sorted(failed_dir.glob("*.mp4"))

    return video_files


def validate_video_file(video_path: Path, min_size_mb: float = 1.0) -> bool:
    """
    Basic validation - check if file exists and is not too small.

    Args:
        video_path: Path to video file
        min_size_mb: Minimum file size in MB

    Returns:
        True if valid, False otherwise
    """
    if not video_path.exists():
        logger.warning(f"File does not exist: {video_path}")
        return False

    file_size_mb = video_path.stat().st_size / (1024 * 1024)

    if file_size_mb < min_size_mb:
        logger.warning(f"File too small ({file_size_mb:.2f} MB): {video_path.name}")
        return False

    return True


def upload_video(
    controller: UploadController,
    video_path: Path,
    dry_run: bool = True,
) -> bool:
    """
    Upload a single video file.

    Args:
        controller: UploadController instance
        video_path: Path to video file
        dry_run: If True, only simulate upload

    Returns:
        True if successful, False otherwise
    """
    filename = video_path.name
    file_size_mb = video_path.stat().st_size / (1024 * 1024)

    # Extract or generate timestamp
    timestamp = extract_timestamp_from_filename(filename)

    logger.info(f"{'[DRY RUN] ' if dry_run else ''}Uploading: {filename}")
    logger.info(f"  Size: {file_size_mb:.2f} MB")
    logger.info(f"  Timestamp: {timestamp}")

    if dry_run:
        logger.info("  [SKIPPED - dry run mode]")
        return True

    try:
        # Upload video
        result = controller.upload_video(
            video_path=str(video_path),
            timestamp=timestamp,
        )

        if result.success:
            youtube_url = f"https://youtu.be/{result.video_id}"
            logger.info(f"  ✅ SUCCESS: {youtube_url}")
            logger.info(f"  Upload duration: {result.upload_duration:.1f}s")
            return True
        else:
            logger.error(f"  ❌ FAILED: {result.error_message}")
            return False

    except Exception as e:
        logger.error(f"  ❌ EXCEPTION: {e}", exc_info=True)
        return False


def move_to_uploaded(video_path: Path, uploaded_dir: Path) -> bool:
    """
    Move video to uploaded directory after successful upload.

    Args:
        video_path: Source video path
        uploaded_dir: Destination directory

    Returns:
        True if successful
    """
    try:
        uploaded_dir.mkdir(parents=True, exist_ok=True)
        dest_path = uploaded_dir / video_path.name

        # Handle duplicate filenames
        if dest_path.exists():
            timestamp = int(time.time())
            stem = video_path.stem
            dest_path = uploaded_dir / f"{stem}_{timestamp}{video_path.suffix}"

        video_path.rename(dest_path)
        logger.info(f"  Moved to: {dest_path}")
        return True

    except Exception as e:
        logger.error(f"  Failed to move file: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Upload all failed videos directly from temp_videos/failed/",
        epilog="""
Examples:
  %(prog)s                        # Dry run - show what would be uploaded
  %(prog)s --upload               # Actually upload all videos
  %(prog)s --upload --move-after  # Upload and move successful ones to uploaded/
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--upload",
        action="store_true",
        help="Actually upload videos (default is dry run)",
    )

    parser.add_argument(
        "--move-after",
        action="store_true",
        help="Move successfully uploaded videos to uploaded/ directory",
    )

    parser.add_argument(
        "--failed-dir",
        type=str,
        default="temp_videos/failed",
        help="Path to failed videos directory (default: temp_videos/failed)",
    )

    parser.add_argument(
        "--min-size",
        type=float,
        default=1.0,
        help="Minimum file size in MB (default: 1.0)",
    )

    args = parser.parse_args()

    # Determine base directory
    script_dir = Path(__file__).parent.parent
    failed_dir = script_dir / args.failed_dir
    uploaded_dir = script_dir / "temp_videos" / "uploaded"

    # Banner
    logger.info("=" * 70)
    logger.info("Upload Failed Videos - Maintenance Script")
    logger.info("=" * 70)
    logger.info(f"Mode: {'UPLOAD' if args.upload else 'DRY RUN'}")
    logger.info(f"Failed directory: {failed_dir}")
    logger.info(f"Move after upload: {args.move_after}")
    logger.info("=" * 70)

    # Get video files
    logger.info("\n🔍 Scanning for failed videos...")
    video_files = get_failed_videos(failed_dir)

    if not video_files:
        logger.info("✓ No videos found in failed directory")
        return 0

    logger.info(f"Found {len(video_files)} video file(s)\n")

    # Validate files
    logger.info("📋 Validating files...")
    valid_videos = []
    for video_path in video_files:
        if validate_video_file(video_path, args.min_size):
            valid_videos.append(video_path)
            logger.info(f"  ✓ {video_path.name}")
        else:
            logger.warning(f"  ✗ {video_path.name} (skipped)")

    if not valid_videos:
        logger.error("\n❌ No valid videos to upload")
        return 1

    logger.info(f"\n✓ {len(valid_videos)} valid video(s) ready for upload\n")

    if not args.upload:
        logger.info("=" * 70)
        logger.info("DRY RUN MODE - No uploads performed")
        logger.info("Run with --upload to actually upload these videos")
        logger.info("=" * 70)
        return 0

    # Initialize upload controller
    logger.info("🚀 Initializing upload controller...")
    try:
        controller = UploadController()
        if not controller.uploader.is_available():
            logger.error("❌ Uploader not available - check credentials and network")
            return 1
        logger.info("✓ Upload controller ready\n")
    except Exception as e:
        logger.error(f"❌ Failed to initialize uploader: {e}", exc_info=True)
        return 1

    # Upload videos
    logger.info("=" * 70)
    logger.info(f"📤 Uploading {len(valid_videos)} video(s)...")
    logger.info("=" * 70)

    results = {
        "success": 0,
        "failed": 0,
        "moved": 0,
    }

    for i, video_path in enumerate(valid_videos, 1):
        logger.info(f"\n[{i}/{len(valid_videos)}] Processing: {video_path.name}")
        logger.info("-" * 70)

        success = upload_video(controller, video_path, dry_run=False)

        if success:
            results["success"] += 1

            # Optionally move to uploaded directory
            if args.move_after:
                if move_to_uploaded(video_path, uploaded_dir):
                    results["moved"] += 1
        else:
            results["failed"] += 1

        # Small delay between uploads
        if i < len(valid_videos):
            time.sleep(2)

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("📊 UPLOAD SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total videos: {len(valid_videos)}")
    logger.info(f"✅ Successful: {results['success']}")
    logger.info(f"❌ Failed: {results['failed']}")
    if args.move_after:
        logger.info(f"📦 Moved: {results['moved']}")
    logger.info("=" * 70)

    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
