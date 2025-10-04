"""
Video Capture Interface

Abstract interface for video capture implementations.
Defines the contract that any video capture system must follow.

This demonstrates Dependency Inversion Principle - high-level code
(RecordingSession) depends on this abstraction, not on FFmpeg directly.

Why an interface?
1. Testability: Can use MockCapture instead of real FFmpeg
2. Flexibility: Easy to swap FFmpeg for other capture methods
3. Clear contract: Documents exactly what a capture system must do
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class VideoCaptureInterface(ABC):
    """
    Abstract base class for video capture systems.

    Any video capture implementation (FFmpeg, GStreamer, OpenCV, etc.)
    must implement all these methods to work with RecordingSession.
    """

    @abstractmethod
    def start_capture(
        self,
        output_file: Path,
        duration: Optional[float] = None
    ) -> bool:
        """
        Start capturing video to file.

        This should be NON-BLOCKING - returns immediately after starting.
        Video capture happens in background process/thread.

        Args:
            output_file: Path where video file will be saved
            duration: Optional max duration in seconds (None = infinite)

        Returns:
            True if capture started successfully, False otherwise

        Raises:
            CaptureError: If camera not available or other critical error

        Example:
            capture.start_capture(Path("video.mp4"), duration=600)
        """
        pass

    @abstractmethod
    def stop_capture(self) -> bool:
        """
        Stop current video capture.

        Should wait for capture process to finish cleanly (finalize file).
        This may block briefly while file is being closed.

        Returns:
            True if stopped successfully, False if no capture was running

        Example:
            capture.stop_capture()  # Waits for file to be finalized
        """
        pass

    @abstractmethod
    def is_capturing(self) -> bool:
        """
        Check if currently capturing video.

        Returns:
            True if capture is active, False otherwise

        Example:
            if capture.is_capturing():
                print("Recording in progress")
        """
        pass

    @abstractmethod
    def get_capture_duration(self) -> float:
        """
        Get duration of current capture in seconds.

        Returns:
            Seconds since capture started, or 0.0 if not capturing

        Example:
            duration = capture.get_capture_duration()
            print(f"Recorded {duration:.1f} seconds")
        """
        pass

    @abstractmethod
    def get_output_file(self) -> Optional[Path]:
        """
        Get path to current output file.

        Returns:
            Path to output file if capturing, None otherwise

        Example:
            if capture.is_capturing():
                print(f"Recording to: {capture.get_output_file()}")
        """
        pass

    @abstractmethod
    def check_health(self) -> dict:
        """
        Check health of capture process.

        Should return information about capture status, any errors,
        frame rate, etc. Used for monitoring during recording.

        Returns:
            Dictionary with health information:
            {
                'is_healthy': bool,
                'error_message': str or None,
                'frames_captured': int,
                'fps': float,
                'file_size_mb': float,
            }

        Example:
            health = capture.check_health()
            if not health['is_healthy']:
                print(f"Capture error: {health['error_message']}")
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if video capture system is available.

        Should check:
        - Is capture software installed? (FFmpeg, etc.)
        - Is camera device present?
        - Are permissions correct?

        Returns:
            True if capture can be used, False otherwise

        Example:
            if not capture.is_available():
                print("ERROR: FFmpeg not installed")
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up resources and stop any active captures.

        Called when shutting down. Should:
        - Stop any active capture
        - Release camera device
        - Clean up temporary files

        This should never raise exceptions.

        Example:
            try:
                # ... use capture ...
            finally:
                capture.cleanup()  # Always cleanup
        """
        pass


class CaptureError(Exception):
    """
    Exception raised for video capture errors.

    Examples:
    - Camera not found
    - FFmpeg not installed
    - Disk full
    - Camera already in use
    """
    pass


class CameraNotFoundError(CaptureError):
    """Camera device not found or not accessible"""
    pass


class CameraBusyError(CaptureError):
    """Camera is already in use by another process"""
    pass


class StorageFullError(CaptureError):
    """Not enough disk space for recording"""
    pass


class CaptureProcessError(CaptureError):
    """Error in capture process (FFmpeg crashed, etc.)"""
    pass
