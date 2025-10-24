"""
FFmpeg Video Capture Implementation

Real video capture using FFmpeg subprocess.
Captures video from USB webcam and encodes to file.

This wraps FFmpeg to match our VideoCaptureInterface.
"""

import logging
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional, Union

from recording.constants import (
    CAMERA_WARMUP_TIME,
    DEFAULT_CAMERA_DEVICE,
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
    get_ffmpeg_command,
    validate_camera_device,
)
from recording.interfaces.video_capture_interface import (
    CameraBusyError,
    CameraNotFoundError,
    CaptureError,
    CaptureProcessError,
    VideoCaptureInterface,
)


class FFmpegCapture(VideoCaptureInterface):
    """
    Video capture using FFmpeg.

    Uses subprocess to run FFmpeg, capturing video from USB webcam
    to a file. Non-blocking - FFmpeg runs in background process.

    Usage:
        capture = FFmpegCapture(camera_device="/dev/video0")
        capture.start_capture(Path("video.mp4"), duration=600)
        # ... recording happens in background ...
        capture.stop_capture()
        capture.cleanup()
    """

    def __init__(
        self,
        camera_device: str = DEFAULT_CAMERA_DEVICE,
        width: int = VIDEO_WIDTH,
        height: int = VIDEO_HEIGHT,
        fps: int = VIDEO_FPS,
    ):
        """
        Initialize FFmpeg capture.

        Args:
            camera_device: Path to camera device (e.g., /dev/video0)
            width: Video width in pixels
            height: Video height in pixels
            fps: Frame rate
        """
        self.logger = logging.getLogger(__name__)

        # Configuration
        self.camera_device = camera_device
        self.width = width
        self.height = height
        self.fps = fps

        # State tracking
        self._process: Optional[subprocess.Popen] = None
        self._output_file: Optional[Path] = None
        self._start_time: Optional[float] = None
        self._target_duration: Optional[float] = None

        self.logger.info(
            f"FFmpeg Capture initialized "
            f"(camera: {camera_device}, resolution: {width}x{height}, fps: {fps})",
        )

    def start_capture(
        self,
        output_file: Path,
        duration: Optional[float] = None,
    ) -> bool:
        """
        Start capturing video with FFmpeg.

        Launches FFmpeg subprocess in background.
        Returns immediately - capture happens asynchronously.
        """
        # Check if already capturing
        if self.is_capturing():
            self.logger.error("Already capturing, cannot start new capture")
            return False

        # Validate camera is available
        if not validate_camera_device(self.camera_device):
            raise CameraNotFoundError(
                f"Camera device not found: {self.camera_device}",
            )

        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Build FFmpeg command
        command = get_ffmpeg_command(
            input_device=self.camera_device,
            output_file=str(output_file),
            width=self.width,
            height=self.height,
            fps=self.fps,
        )

        # Add duration limit if specified
        if duration:
            # Insert -t (duration) option before output file
            command.insert(-1, "-t")
            command.insert(-1, str(duration))

        self.logger.info(f"Starting FFmpeg capture to: {output_file}")
        self.logger.debug(f"FFmpeg command: {' '.join(command)}")

        try:
            # Start FFmpeg process
            self._process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,  # Don't wait for stdin
            )

            # Give FFmpeg time to initialize
            time.sleep(CAMERA_WARMUP_TIME)

            # Check if process is still running (didn't crash immediately)
            if self._process.poll() is not None:
                # Process exited already - something went wrong
                stdout, stderr = self._process.communicate()
                error_msg = stderr.decode("utf-8", errors="ignore")

                if "Device or resource busy" in error_msg:
                    raise CameraBusyError(
                        f"Camera is busy: {self.camera_device}",
                    )
                raise CaptureProcessError(
                    f"FFmpeg failed to start: {error_msg}",
                )

            # Success - track state
            self._output_file = output_file
            self._start_time = time.time()
            self._target_duration = duration

            self.logger.info(
                f"Capture started successfully "
                f"(PID: {self._process.pid}, duration: {duration or 'unlimited'}s)",
            )
            return True

        except FileNotFoundError:
            raise CaptureError(
                "FFmpeg not found. Install with: sudo apt-get install ffmpeg",
            )
        except Exception as e:
            self.logger.error(f"Failed to start capture: {e}")
            self._cleanup_failed_capture()
            raise

    def stop_capture(self) -> bool:
        """
        Stop FFmpeg capture gracefully.

        Sends SIGTERM to FFmpeg, waits for it to finalize the file.
        This may block briefly (1-2 seconds) while FFmpeg closes the file.
        """
        if not self.is_capturing():
            self.logger.warning("Not capturing, nothing to stop")
            return False

        # At this point, self._process is guaranteed to be non-None by is_capturing()
        assert self._process is not None

        self.logger.info("Stopping capture...")

        try:
            # Send termination signal to FFmpeg
            # FFmpeg handles SIGTERM gracefully and finalizes the file
            self._process.terminate()

            # Wait for process to finish (with timeout)
            try:
                stdout, stderr = self._process.communicate(timeout=5.0)

                # Check exit code
                if self._process.returncode != 0:
                    error_msg = stderr.decode("utf-8", errors="ignore")
                    self.logger.warning(
                        f"FFmpeg exited with code {self._process.returncode}: "
                        f"{error_msg}",
                    )
                else:
                    self.logger.info("Capture stopped successfully")

            except subprocess.TimeoutExpired:
                # FFmpeg didn't stop gracefully, force kill
                self.logger.warning("FFmpeg didn't stop gracefully, force killing")
                self._process.kill()
                self._process.wait()

            # Verify file was created
            if self._output_file and self._output_file.exists():
                file_size_mb = self._output_file.stat().st_size / (1024 * 1024)
                self.logger.info(
                    f"Recording saved: {self._output_file} ({file_size_mb:.1f} MB)",
                )
            else:
                self.logger.error("Output file was not created!")

            return True

        except Exception as e:
            self.logger.error(f"Error stopping capture: {e}")
            return False

        finally:
            # Reset state
            self._process = None
            self._output_file = None
            self._start_time = None
            self._target_duration = None

    def is_capturing(self) -> bool:
        """
        Check if FFmpeg process is running.
        """
        if self._process is None:
            return False

        # Check if process is still alive
        return self._process.poll() is None

    def get_capture_duration(self) -> float:
        """
        Get seconds since capture started.
        """
        if not self.is_capturing() or self._start_time is None:
            return 0.0

        return time.time() - self._start_time

    def get_output_file(self) -> Optional[Path]:
        """
        Get current output file path.
        """
        return self._output_file

    def check_health(self) -> dict:
        """
        Check FFmpeg process health.

        Returns health information including process status,
        file size, and any errors.
        """
        health: dict[str, Union[bool, str, int, float, None]] = {
            "is_healthy": True,
            "error_message": None,
            "frames_captured": 0,  # FFmpeg doesn't easily expose this
            "fps": self.fps,
            "file_size_mb": 0.0,
        }

        # Check if process is running
        if not self.is_capturing():
            health["is_healthy"] = False
            health["error_message"] = "Capture not running"
            return health

        # Check if process crashed
        assert self._process is not None
        if self._process.poll() is not None:
            # Process exited unexpectedly
            health["is_healthy"] = False
            try:
                stdout, stderr = self._process.communicate(timeout=1.0)
                error_msg = stderr.decode("utf-8", errors="ignore")
                health["error_message"] = f"FFmpeg crashed: {error_msg}"
            except:
                health["error_message"] = "FFmpeg crashed (unknown error)"
            return health

        # Check file size (indicates frames are being written)
        if self._output_file and self._output_file.exists():
            file_size_bytes = self._output_file.stat().st_size
            health["file_size_mb"] = file_size_bytes / (1024 * 1024)

            # If file size is 0 after warmup, something's wrong
            if health["file_size_mb"] == 0.0 and self.get_capture_duration() > 2.0:
                health["is_healthy"] = False
                health["error_message"] = "No data being written to file"

        return health

    def is_available(self) -> bool:
        """
        Check if FFmpeg and camera are available.
        """
        # Check if FFmpeg is installed
        if not shutil.which("ffmpeg"):
            self.logger.warning("FFmpeg not found in PATH")
            return False

        # Check if camera device exists
        if not validate_camera_device(self.camera_device):
            self.logger.warning(f"Camera not found: {self.camera_device}")
            return False

        return True

    def cleanup(self) -> None:
        """
        Stop capture and clean up resources.
        """
        self.logger.info("Cleaning up FFmpeg Capture")

        # Stop any active capture
        if self.is_capturing():
            self.stop_capture()

        self.logger.info("FFmpeg Capture cleanup complete")

    def _cleanup_failed_capture(self) -> None:
        """
        Internal cleanup after failed capture attempt.
        """
        if self._process:
            try:
                self._process.kill()
                self._process.wait(timeout=1.0)
            except:
                pass
            self._process = None

        self._output_file = None
        self._start_time = None
        self._target_duration = None

    def get_camera_info(self) -> dict:
        """
        Get information about the camera device.

        Returns:
            Dictionary with camera information
        """
        info = {
            "device": self.camera_device,
            "exists": validate_camera_device(self.camera_device),
            "configured_resolution": f"{self.width}x{self.height}",
            "configured_fps": self.fps,
        }

        # Try to get actual camera capabilities using v4l2-ctl
        # This is optional - if v4l2-ctl not installed, just skip
        try:
            if shutil.which("v4l2-ctl"):
                result = subprocess.run(
                    ["v4l2-ctl", "-d", self.camera_device, "--list-formats-ext"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                )
                if result.returncode == 0:
                    info["capabilities"] = result.stdout
        except:
            pass  # Optional info, don't fail if we can't get it

        return info

    def __del__(self):
        """Destructor - ensure cleanup"""
        self.cleanup()
