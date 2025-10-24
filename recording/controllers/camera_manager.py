"""
Camera Manager

High-level camera control and lifecycle management.
Wraps video capture interface with health monitoring and error handling.

SOLID Principles:
- Single Responsibility: Only manages camera lifecycle
- Dependency Inversion: Depends on VideoCaptureInterface
- Open/Closed: Easy to add monitoring features
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from recording.constants import DEFAULT_CAMERA_DEVICE
from recording.factory import create_capture
from recording.interfaces.video_capture_interface import (
    CaptureError,
    VideoCaptureInterface,
)


class CameraManager:
    """
    Manages camera lifecycle and health monitoring.

    This is a thin wrapper around VideoCaptureInterface that adds:
    - Health monitoring
    - Error recovery
    - Status reporting
    - Logging

    Usage:
        camera = CameraManager()
        if camera.is_ready():
            camera.start_recording(Path("video.mp4"), duration=600)
            # ... recording happens ...
            camera.stop_recording()
        camera.cleanup()
    """

    def __init__(
        self,
        capture: Optional[VideoCaptureInterface] = None,
        camera_device: str = DEFAULT_CAMERA_DEVICE,
    ):
        """
        Initialize camera manager.

        Args:
            capture: Video capture interface, or None to auto-create
            camera_device: Camera device path (used if creating capture)

        Example:
            # Normal usage - auto-creates capture
            camera = CameraManager()

            # Testing with mock
            mock = MockCapture()
            camera = CameraManager(capture=mock)
        """
        self.logger = logging.getLogger(__name__)
        self.camera_device = camera_device

        # Create or use provided capture interface
        self.capture = capture or create_capture()

        # Health monitoring
        self._last_health_check: Optional[Dict[str, Any]] = None
        self._consecutive_health_failures = 0
        self._max_health_failures = 3  # Alert after 3 consecutive failures

        self.logger.info(
            f"Camera Manager initialized "
            f"(device: {camera_device}, "
            f"capture available: {self.capture.is_available()})",
        )

    def is_ready(self) -> bool:
        """
        Check if camera is ready to record.

        Verifies:
        - Capture system is available
        - Not currently recording

        Returns:
            True if ready to start recording, False otherwise

        Example:
            if camera.is_ready():
                camera.start_recording(output_file)
        """
        # Check capture is available
        if not self.capture.is_available():
            self.logger.warning("Camera not available")
            return False

        # Check not already recording
        if self.capture.is_capturing():
            self.logger.warning("Already recording")
            return False

        return True

    def start_recording(
        self,
        output_file: Path,
        duration: Optional[float] = None,
    ) -> bool:
        """
        Start recording video.

        Args:
            output_file: Path where video will be saved
            duration: Optional max duration in seconds

        Returns:
            True if recording started, False otherwise

        Raises:
            CaptureError: If camera fails to start

        Example:
            success = camera.start_recording(
                Path("/recordings/video.mp4"),
                duration=600
            )
        """
        # Check readiness
        if not self.is_ready():
            self.logger.error("Camera not ready to record")
            return False

        try:
            # Start capture
            success = self.capture.start_capture(output_file, duration)

            if success:
                self.logger.info(
                    f"Recording started: {output_file.name} "
                    f"(duration: {duration or 'unlimited'}s)",
                )
                # Reset health monitoring
                self._consecutive_health_failures = 0
                self._last_health_check = None
            else:
                self.logger.error("Failed to start recording")

            return success

        except CaptureError as e:
            self.logger.error(f"Camera error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error starting recording: {e}")
            return False

    def stop_recording(self) -> bool:
        """
        Stop current recording.

        Returns:
            True if stopped successfully, False if not recording

        Example:
            camera.stop_recording()
        """
        if not self.capture.is_capturing():
            self.logger.warning("Not recording, nothing to stop")
            return False

        try:
            success = self.capture.stop_capture()

            if success:
                self.logger.info("Recording stopped")
            else:
                self.logger.warning("Failed to stop recording properly")

            # Reset health tracking
            self._consecutive_health_failures = 0
            self._last_health_check = None

            return success

        except Exception as e:
            self.logger.error(f"Error stopping recording: {e}")
            return False

    def is_recording(self) -> bool:
        """
        Check if currently recording.

        Returns:
            True if recording active, False otherwise
        """
        return self.capture.is_capturing()

    def get_recording_duration(self) -> float:
        """
        Get duration of current recording in seconds.

        Returns:
            Seconds since recording started, or 0.0 if not recording

        Example:
            duration = camera.get_recording_duration()
            print(f"Recorded {duration:.1f} seconds")
        """
        return self.capture.get_capture_duration()

    def get_output_file(self) -> Optional[Path]:
        """
        Get path to current recording file.

        Returns:
            Path to output file if recording, None otherwise
        """
        return self.capture.get_output_file()

    def check_health(self, force: bool = False) -> Dict[str, Any]:
        """
        Check camera health.

        Monitors recording process for errors and tracks failures.
        Caches result to avoid excessive checks.

        Args:
            force: If True, always check (ignore cache)

        Returns:
            Health information dictionary:
            {
                'is_healthy': bool,
                'error_message': str or None,
                'consecutive_failures': int,
                'frames_captured': int,
                'fps': float,
                'file_size_mb': float,
            }

        Example:
            health = camera.check_health()
            if not health['is_healthy']:
                print(f"Camera error: {health['error_message']}")
        """
        # Use cached result if recent (unless forced)
        if not force and self._last_health_check:
            return self._last_health_check

        # Get health from capture interface
        health = self.capture.check_health()

        # Check if capture crashed (for mock capture testing)
        crashed = False
        if hasattr(self.capture, "_crashed"):
            crashed = self.capture._crashed

        # Track consecutive failures
        if not health["is_healthy"] or crashed:
            self._consecutive_health_failures += 1
            error_msg = health.get("error_message", "Unknown error")
            self.logger.warning(
                f"Camera health check failed "
                f"(failures: {self._consecutive_health_failures}): "
                f"{error_msg}",
            )
        else:
            # Reset counter on success
            if self._consecutive_health_failures > 0:
                self.logger.info("Camera health recovered")
            self._consecutive_health_failures = 0

        # Add failure tracking to health info
        health["consecutive_failures"] = self._consecutive_health_failures
        health["critical"] = (
            self._consecutive_health_failures >= self._max_health_failures
        )

        # Cache result
        self._last_health_check = health

        return health

    def get_status(self) -> Dict[str, Any]:
        """
        Get complete camera status.

        Returns:
            Dictionary with status information:
            {
                'is_available': bool,
                'is_ready': bool,
                'is_recording': bool,
                'recording_duration': float,
                'output_file': str or None,
                'health': dict,
            }

        Example:
            status = camera.get_status()
            print(f"Recording: {status['is_recording']}")
            print(f"Duration: {status['recording_duration']:.1f}s")
        """
        return {
            "is_available": self.capture.is_available(),
            "is_ready": self.is_ready(),
            "is_recording": self.is_recording(),
            "recording_duration": self.get_recording_duration(),
            "output_file": (
                str(self.get_output_file()) if self.get_output_file() else None
            ),
            "health": self.check_health(),
        }

    def get_camera_info(self) -> Dict[str, Any]:
        """
        Get camera device information.

        Returns camera capabilities and configuration.
        Only works with FFmpegCapture.

        Returns:
            Dictionary with camera information
        """
        # Try to get camera info if available
        if hasattr(self.capture, "get_camera_info"):
            return self.capture.get_camera_info()

        # Fallback for other capture types
        return {
            "device": self.camera_device,
            "available": self.capture.is_available(),
        }

    def cleanup(self) -> None:
        """
        Stop recording and clean up resources.

        Always call this before shutting down!

        Example:
            camera = CameraManager()
            try:
                # ... use camera ...
            finally:
                camera.cleanup()
        """
        self.logger.info("Cleaning up Camera Manager")

        # Stop any active recording
        if self.is_recording():
            self.stop_recording()

        # Cleanup capture interface
        try:
            self.capture.cleanup()
        except Exception as e:
            self.logger.error(f"Error during capture cleanup: {e}")

        self.logger.info("Camera Manager cleanup complete")

    def __del__(self):
        """Destructor - ensure cleanup"""
        self.cleanup()
