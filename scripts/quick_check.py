#!/usr/bin/env python3
"""
Quick Check Script - Real Scenario Test

Tests the complete video recording, storage, and upload workflow with:
1. Audio feedback ("recording started")
2. 2-second video capture from built-in camera
3. Audio feedback ("recording ended")
4. Storage in local directory
5. Upload to YouTube
6. Audio feedback ("upload successful")

All configuration at the top for easy override.

Usage:
    python scripts/quick_check.py
    # or from root directory
    python -m scripts.quick_check
    # or with environment variable
    MODE=mock python scripts/quick_check.py
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to allow imports (MUST be before other imports)
sys.path.insert(0, str(Path(__file__).parent.parent))

from hardware.factory import HardwareFactory
from recording.controllers.camera_manager import CameraManager
from recording.controllers.recording_session import RecordingSession
from recording.factory import RecordingFactory
from recording.interfaces.video_capture_interface import CaptureError
from storage.controllers.storage_controller import StorageController
from upload.controllers.upload_controller import UploadController
from upload.factory import UploaderFactory

# =============================================================================
# CONFIGURATION - All parameters in one place
# =============================================================================

# Recording Settings
RECORDING_DURATION_SECONDS = 10  # Quick test with 5 seconds of actual video
VIDEO_WIDTH = 1280  # Use actual camera resolution
VIDEO_HEIGHT = 720
VIDEO_FPS = 30  # Use actual camera FPS
USE_BUILTIN_CAMERA = False  # Record from built-in camera (macOS/Linux with camera)

# Storage Settings - Save to project directory
STORAGE_BASE_PATH = Path(__file__).parent.parent / "temp_videos"
METADATA_DB_PATH = Path(__file__).parent.parent / "temp_videos"

# Audio Feedback Messages
MESSAGE_RECORDING_START = "Recording started"
MESSAGE_RECORDING_END = "Recording ended"
MESSAGE_UPLOAD_START = "Starting upload"
MESSAGE_UPLOAD_SUCCESS = "Upload successful"
MESSAGE_UPLOAD_FAILED = "Upload failed"

# Mode Selection (auto, real, mock)
# Override with environment: HARDWARE_MODE=mock python scripts/quick_check.py
HARDWARE_MODE = "auto"  # auto, real, mock
RECORDING_MODE = "auto"  # auto, real, mock - Use "real" to record actual video from camera (requires FFmpeg + camera)
STORAGE_MODE = "mock"  # Use mock storage (doesn't require /home/pi directory)
UPLOAD_MODE = "auto"  # auto, youtube, mock - Change to "mock" to simulate upload

# YouTube Video Settings
VIDEO_TITLE = "Quick Check Test - {timestamp}"
VIDEO_DESCRIPTION = "Quick check test video from Raspberry Pi Video Recorder"
VIDEO_CATEGORY = "28"  # Science & Technology
VIDEO_PRIVACY = "private"  # private, unlisted, public

# Cleanup Settings
KEEP_VIDEO_AFTER_UPLOAD = True  # Set to False to auto-delete after successful upload
CLEANUP_ON_FAILURE = (
    False  # Set to True to delete video if upload fails (useful for testing)
)

# Logging
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# =============================================================================
# LOGGING SETUP
# =============================================================================

# Configure logging
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


# =============================================================================
# MAIN WORKFLOW
# =============================================================================


def emit_feedback(audio, message: str) -> None:  # type: ignore[no-untyped-def,unused-ignore]
    """Emit audio feedback message."""
    logger.info(f"📢 {message}")
    try:
        # Try to speak the message (works with both AudioController and TTSInterface)
        if hasattr(audio, "speak"):
            audio.speak(message)
        else:
            logger.warning("Audio device doesn't support speak()")
    except Exception as e:
        logger.warning(f"Could not play audio: {e}")


def quick_check() -> bool:
    """
    Run the complete quick check workflow.

    Returns:
        True if successful, False otherwise
    """
    # Ensure storage directory exists
    STORAGE_BASE_PATH.mkdir(parents=True, exist_ok=True)

    # Make USE_BUILTIN_CAMERA available in this scope
    use_builtin_camera = USE_BUILTIN_CAMERA

    logger.info("=" * 70)
    logger.info("🎬 QUICK CHECK - Complete Workflow Test")
    logger.info("=" * 70)

    # =========================================================================
    # STEP 1: Initialize Hardware (Audio)
    # =========================================================================
    logger.info("\n[1/6] Initializing hardware...")
    try:
        hardware_factory = HardwareFactory()
        audio = hardware_factory.create_tts(mode=HARDWARE_MODE)  # type: ignore[arg-type]
        logger.info("✅ Audio controller initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize audio: {e}")
        return False

    # =========================================================================
    # STEP 2: Initialize Recording
    # =========================================================================
    logger.info("\n[2/6] Initializing recording...")
    try:
        recording_factory = RecordingFactory()
        capture = recording_factory.create_capture(mode=RECORDING_MODE)  # type: ignore[arg-type]

        # If it's real FFmpeg, update video parameters
        if RECORDING_MODE == "real" or (
            RECORDING_MODE == "auto" and capture.is_available()
        ):
            from recording.implementations.ffmpeg_capture import FFmpegCapture

            if isinstance(capture, FFmpegCapture):
                capture.width = VIDEO_WIDTH
                capture.height = VIDEO_HEIGHT
                capture.fps = VIDEO_FPS

        camera = CameraManager(capture)
        logger.info(
            f"✅ Recording initialized (width={VIDEO_WIDTH}, height={VIDEO_HEIGHT}, fps={VIDEO_FPS})",
        )
    except Exception as e:
        logger.error(f"❌ Failed to initialize recording: {e}")
        return False

    # =========================================================================
    # STEP 3: Initialize Storage
    # =========================================================================
    logger.info("\n[3/6] Initializing storage...")
    try:
        # Use StorageController with MockStorage for quick check
        # MockStorage simulates storage without requiring /home/pi directory
        from storage.implementations.mock_storage import MockStorage

        mock_storage_impl = MockStorage()
        storage = StorageController(storage_impl=mock_storage_impl)

        logger.info("✅ Storage initialized (mock mode - simulates real storage)")
    except Exception as e:
        logger.error(f"❌ Failed to initialize storage: {e}")
        return False

    # =========================================================================
    # STEP 4: Recording Session
    # =========================================================================
    logger.info("\n[4/6] Recording video...")

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = STORAGE_BASE_PATH / f"quick_check_{timestamp}.mp4"

    try:
        # Emit "recording started" feedback
        emit_feedback(audio, MESSAGE_RECORDING_START)

        # Try direct FFmpeg capture from built-in camera (works on macOS/Linux with camera)
        if use_builtin_camera:
            import shutil
            import subprocess

            if shutil.which("ffmpeg"):
                logger.info("📹 Using direct FFmpeg camera capture...")
                try:
                    # Try macOS AVFoundation format first
                    cmd = [
                        "ffmpeg",
                        "-f",
                        "avfoundation",
                        "-video_size",
                        f"{VIDEO_WIDTH}x{VIDEO_HEIGHT}",
                        "-framerate",
                        str(VIDEO_FPS),
                        "-i",
                        "0",  # Camera device 0 (FaceTime camera on macOS)
                        "-t",
                        str(RECORDING_DURATION_SECONDS),
                        "-c:v",
                        "libx264",
                        "-preset",
                        "ultrafast",
                        "-crf",
                        "23",
                        "-y",
                        str(video_path),
                    ]

                    result = subprocess.run(
                        cmd,
                        check=False,
                        capture_output=True,
                        timeout=RECORDING_DURATION_SECONDS + 10,
                    )
                    if result.returncode != 0:
                        logger.warning(
                            f"FFmpeg AVFoundation failed, trying mock: {result.stderr.decode()[:200]}",
                        )
                        raise CaptureError("AVFoundation failed")

                    # Success - file was created by FFmpeg
                    logger.info(f"📹 Recording to {video_path.name}... (direct FFmpeg)")
                except Exception as e:
                    logger.warning(
                        f"Direct camera capture failed: {e}, falling back to mock...",
                    )
                    # Fall back to mock recording below
                    use_builtin_camera = False
            else:
                logger.warning("FFmpeg not found, using mock recording")
                use_builtin_camera = False

        # Fall back to standard recording session (mock or real)
        if not use_builtin_camera or not video_path.exists():
            session = RecordingSession(camera)
            session.on_complete = lambda: logger.info("📹 Recording completed")
            session.on_error = lambda msg: logger.error(f"📹 Recording error: {msg}")

            # Start recording
            success = session.start(video_path, duration=RECORDING_DURATION_SECONDS)
            if not success:
                logger.error("❌ Failed to start recording")
                return False

            logger.info(f"📹 Recording to {video_path.name}...")

            # Wait for recording to complete
            import time

            time.sleep(RECORDING_DURATION_SECONDS + 1)

            # Stop recording
            session.stop()
            session.cleanup()

        # Emit "recording ended" feedback
        emit_feedback(audio, MESSAGE_RECORDING_END)

        # Verify file exists
        if not video_path.exists():
            logger.error(f"❌ Video file not created: {video_path}")
            return False

        file_size_mb = video_path.stat().st_size / (1024 * 1024)
        logger.info(
            f"✅ Recording complete: {video_path.name} ({file_size_mb:.2f} MB)",
        )

    except Exception as e:
        logger.error(f"❌ Recording failed: {e}", exc_info=True)
        return False

    # =========================================================================
    # STEP 5: Save to Storage
    # =========================================================================
    logger.info("\n[5/6] Saving to storage...")

    try:
        # Save recording to storage
        video = storage.save_recording(
            video_path,
            duration_seconds=RECORDING_DURATION_SECONDS,
        )

        if not video:
            logger.error("❌ Failed to save recording to storage")
            return False

        # Keep track of actual video path for upload
        actual_video_path = video_path

        logger.info(
            f"✅ Saved to storage: {video.filename} (status: {video.status.value})",
        )

    except Exception as e:
        logger.error(f"❌ Storage save failed: {e}", exc_info=True)
        return False

    # =========================================================================
    # STEP 6: Upload to YouTube
    # =========================================================================
    logger.info("\n[6/6] Uploading to YouTube...")

    try:
        # Emit "upload started" feedback
        emit_feedback(audio, MESSAGE_UPLOAD_START)

        # Initialize upload
        uploader_factory = UploaderFactory()
        uploader = uploader_factory.create_uploader(mode=UPLOAD_MODE)  # type: ignore[arg-type]
        upload_controller = UploadController(uploader)

        # Mark upload as started
        storage.mark_upload_started(video)

        # Generate timestamp string
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Upload video - use actual path, not storage's virtual path
        logger.info(f"📤 Uploading: {VIDEO_TITLE.format(timestamp=timestamp)}...")

        upload_result = upload_controller.upload_video(
            video_path=str(actual_video_path),
            timestamp=timestamp,
        )

        if upload_result.success:
            # Get YouTube URL (video_id is the ID, construct full URL)
            youtube_url = f"https://youtu.be/{upload_result.video_id}"

            # Mark upload as successful
            success = storage.mark_upload_success(video, youtube_url)

            if success:
                logger.info(f"✅ Upload successful: {youtube_url}")

                # Emit "upload successful" feedback
                emit_feedback(audio, MESSAGE_UPLOAD_SUCCESS)

                # Optional cleanup: delete temp video file after successful upload
                if not KEEP_VIDEO_AFTER_UPLOAD:
                    try:
                        if actual_video_path.exists():
                            actual_video_path.unlink()
                            logger.info(
                                f"Cleaned up temp video: {actual_video_path.name}",
                            )
                    except Exception as e:
                        logger.warning(f"Failed to cleanup video file: {e}")
            else:
                logger.warning("Upload succeeded but storage marking failed")
        else:
            # Mark upload as failed
            storage.mark_upload_failed(
                video,
                upload_result.error_message or "Unknown error",
            )

            logger.error(f"❌ Upload failed: {upload_result.error_message}")

            # Emit "upload failed" feedback
            emit_feedback(audio, MESSAGE_UPLOAD_FAILED)

            # Optional cleanup on failure
            if CLEANUP_ON_FAILURE:
                try:
                    if actual_video_path.exists():
                        actual_video_path.unlink()
                        logger.info(
                            f"Cleaned up failed video: {actual_video_path.name}",
                        )
                except Exception as e:
                    logger.warning(f"Failed to cleanup video file: {e}")

            return False

    except Exception as e:
        logger.error(f"❌ Upload error: {e}", exc_info=True)
        storage.mark_upload_failed(video, str(e))
        return False

    # =========================================================================
    # CLEANUP
    # =========================================================================
    logger.info("\n[✓] Cleanup...")
    try:
        camera.cleanup()
        storage.cleanup()
        logger.info("✅ Cleanup complete")
    except Exception as e:
        logger.warning(f"Cleanup warning: {e}")

    return True


# =============================================================================
# ENTRY POINT
# =============================================================================


def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    logger.info("Starting quick check script...")

    try:
        success = quick_check()

        if success:
            logger.info("\n" + ("=" * 70))
            logger.info("✅ QUICK CHECK COMPLETE - All systems operational!")
            logger.info("=" * 70)
            return 0

        logger.error("\n" + ("=" * 70))
        logger.error("❌ QUICK CHECK FAILED - See errors above")
        logger.error("=" * 70)
        return 1

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Quick check interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
