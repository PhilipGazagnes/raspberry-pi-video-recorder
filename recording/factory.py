"""
Recording Factory

Factory pattern for creating recording implementations.
Automatically selects real or mock capture based on availability.

Similar to hardware factory pattern - single place to decide implementation.
"""

import logging
from typing import Literal

from recording.implementations.ffmpeg_capture import FFmpegCapture
from recording.implementations.mock_capture import MockCapture
from recording.interfaces.video_capture_interface import VideoCaptureInterface

# Type alias for better type hints
CaptureMode = Literal["auto", "real", "mock"]


class RecordingFactory:
    """
    Factory for creating video capture implementations.

    Usage:
        # Auto-detect (uses FFmpeg if available, mock otherwise)
        capture = RecordingFactory.create_capture()

        # Force mock mode (useful for testing)
        capture = RecordingFactory.create_capture(mode="mock")

        # Force real capture (raises error if not available)
        capture = RecordingFactory.create_capture(mode="real")
    """

    _logger = logging.getLogger(__name__)

    @classmethod
    def create_capture(
        cls,
        mode: CaptureMode = "auto",
        simulate_timing: bool = True
    ) -> VideoCaptureInterface:
        """
        Create a video capture instance.

        Args:
            mode: "auto" (detect), "real" (force FFmpeg), "mock" (force mock)
            simulate_timing: For mock capture, whether to simulate timing
                           (only used if mode="mock")

        Returns:
            VideoCaptureInterface implementation

        Raises:
            RuntimeError: If mode="real" but FFmpeg not available

        Example:
            # Auto-detect
            capture = RecordingFactory.create_capture()

            # Force mock for testing (fast)
            capture = RecordingFactory.create_capture(
                mode="mock",
                simulate_timing=False
            )
        """
        if mode == "mock":
            cls._logger.info(f"Creating Mock Capture (simulate_timing: {simulate_timing})")
            return MockCapture(simulate_timing=simulate_timing)

        if mode == "real":
            try:
                capture = FFmpegCapture()
                if not capture.is_available():
                    raise RuntimeError("FFmpeg or camera not available")
                cls._logger.info("Creating FFmpeg Capture (forced)")
                return capture
            except Exception as e:
                raise RuntimeError(
                    f"Real capture requested but not available: {e}"
                ) from e

        # mode == "auto" - try real first, fall back to mock
        try:
            capture = FFmpegCapture()
            if capture.is_available():
                cls._logger.info("Creating FFmpeg Capture (auto-detected)")
                return capture
            else:
                cls._logger.warning(
                    "FFmpeg or camera not available, using Mock Capture"
                )
                return MockCapture(simulate_timing=simulate_timing)
        except Exception as e:
            cls._logger.warning(
                f"Real capture not available ({e}), using Mock Capture"
            )
            return MockCapture(simulate_timing=simulate_timing)

    @classmethod
    def is_real_capture_available(cls) -> dict[str, bool]:
        """
        Check if real video capture is available.

        Useful for diagnostics and configuration display.

        Returns:
            Dictionary with availability status:
            {
                'ffmpeg': True/False,
                'camera': True/False
            }

        Example:
            status = RecordingFactory.is_real_capture_available()
            if not status['ffmpeg']:
                print("Warning: FFmpeg not installed")
        """
        status = {
            'ffmpeg': False,
            'camera': False,
        }

        try:
            capture = FFmpegCapture()
            status['ffmpeg'] = True
            status['camera'] = capture.is_available()
            capture.cleanup()
        except Exception:
            pass

        return status


# Convenience functions for quick creation

def create_capture(force_mock: bool = False, fast_mode: bool = False) -> VideoCaptureInterface:
    """
    Quick capture creation with simple options.

    Args:
        force_mock: If True, always use mock
        fast_mode: If True and using mock, skip timing simulation

    Returns:
        Video capture interface

    Example:
        # Normal usage
        capture = create_capture()

        # Fast tests
        capture = create_capture(force_mock=True, fast_mode=True)
    """
    mode = "mock" if force_mock else "auto"
    simulate_timing = not fast_mode
    return RecordingFactory.create_capture(mode=mode, simulate_timing=simulate_timing)
