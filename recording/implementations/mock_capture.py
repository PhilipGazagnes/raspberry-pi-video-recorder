"""
Mock Video Capture Implementation

Simulated video capture for testing without real camera/FFmpeg.
Mimics FFmpeg behavior for unit tests.

This is a "Fake" (test double) - it has working logic but no real hardware.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Optional

from recording.interfaces.video_capture_interface import (
    CaptureError,
    VideoCaptureInterface,
)


class MockCapture(VideoCaptureInterface):
    """
    Mock video capture for testing.

    Simulates FFmpeg capture behavior without actually recording video.
    Creates empty/fake video files for testing file handling logic.

    Usage:
        capture = MockCapture()
        capture.start_capture(Path("test.mp4"), duration=10)
        # ... simulates recording for 10 seconds ...
        capture.stop_capture()
    """

    def __init__(self, simulate_timing: bool = True):
        """
        Initialize mock capture.

        Args:
            simulate_timing: If True, capture duration advances in real-time.
                           If False, duration is instantaneous (faster tests).
        """
        self.logger = logging.getLogger(__name__)
        self.simulate_timing = simulate_timing

        # State tracking
        self._is_capturing = False
        self._output_file: Optional[Path] = None
        self._start_time: Optional[float] = None
        self._target_duration: Optional[float] = None

        # Simulation thread (if using real timing)
        self._capture_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Health tracking
        self._simulated_frames = 0
        self._is_healthy = True
        self._error_message: Optional[str] = None
        self._crashed = False  # Track if capture crashed vs normal stop

        # Configuration for test scenarios
        self._should_fail_start = False
        self._should_crash_during = False
        self._crash_after_seconds: Optional[float] = None

        self.logger.info(
            f"Mock Capture initialized (simulate_timing: {simulate_timing})"
        )

    def start_capture(
        self,
        output_file: Path,
        duration: Optional[float] = None
    ) -> bool:
        """
        Simulate starting video capture.

        Creates empty file and tracks state.
        If simulate_timing=True, spawns thread to track duration.
        """
        # Check if already capturing
        if self._is_capturing:
            self.logger.error("[MOCK] Already capturing")
            return False

        # Simulate start failure if configured
        if self._should_fail_start:
            self.logger.error("[MOCK] Simulated start failure")
            raise CaptureError("Simulated camera failure")

        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Create empty output file (simulates video file)
        output_file.touch()

        # Update state
        self._is_capturing = True
        self._output_file = output_file
        self._start_time = time.time()
        self._target_duration = duration
        self._simulated_frames = 0
        self._is_healthy = True
        self._error_message = None
        self._crashed = False

        self.logger.info(
            f"[MOCK] Capture started: {output_file} "
            f"(duration: {duration or 'unlimited'}s)"
        )

        # If simulating timing, start background thread
        if self.simulate_timing and duration:
            self._stop_event.clear()
            self._capture_thread = threading.Thread(
                target=self._capture_worker,
                args=(duration,),
                daemon=True,
                name="MockCapture-Worker"
            )
            self._capture_thread.start()

        return True

    def _capture_worker(self, duration: float) -> None:
        """
        Background thread that simulates capture duration.

        Automatically stops after duration expires.
        Simulates frame capture for health checks.
        """
        fps = 30  # Simulated frame rate
        frame_interval = 1.0 / fps

        elapsed = 0.0
        while elapsed < duration and not self._stop_event.is_set():
            # Simulate frame capture
            self._simulated_frames += 1

            # Check for simulated crash
            if self._should_crash_during and self._crash_after_seconds:
                if elapsed >= self._crash_after_seconds:
                    self.logger.warning("[MOCK] Simulating capture crash")
                    self._is_healthy = False
                    self._error_message = "Simulated capture crash"
                    self._crashed = True  # Mark as crashed
                    self._is_capturing = False
                    self._finalize_file()
                    return

            # Wait for next frame
            time.sleep(frame_interval)
            elapsed += frame_interval

        # Duration elapsed - auto-stop
        if self._is_capturing and not self._stop_event.is_set():
            self.logger.info("[MOCK] Capture duration elapsed, auto-stopping")
            self._is_capturing = False
            self._finalize_file()

    def _finalize_file(self) -> None:
        """Write fake data to output file."""
        if self._output_file and self._output_file.exists():
            duration = time.time() - self._start_time if self._start_time else 0
            fake_size = int(duration * 4 * 1024 * 1024)  # 4 MB/sec

            with open(self._output_file, 'wb') as f:
                f.write(b'\x00\x00\x00\x20ftypmp42')  # MP4 header
                f.write(b'\x00' * min(fake_size, 10_000_000))  # Cap at 10 MB

            file_size_mb = self._output_file.stat().st_size / (1024 * 1024)
            self.logger.info(f"[MOCK] Recording saved: {file_size_mb:.1f} MB")

    def stop_capture(self) -> bool:
        """
        Stop mock capture.

        Stops background thread if running.
        Simulates file finalization.
        """
        if not self._is_capturing:
            self.logger.warning("[MOCK] Not capturing")
            return False

        self.logger.info("[MOCK] Stopping capture...")

        # Signal thread to stop
        self._stop_event.set()

        # Wait for thread to finish
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=2.0)

        # Mark as stopped (normal stop, not crash)
        self._is_capturing = False
        self._crashed = False  # Normal stop clears crash flag

        # Finalize file if not already done
        self._finalize_file()

        # Reset state
        self._output_file = None
        self._start_time = None
        self._target_duration = None
        self._capture_thread = None

        return True

    def is_capturing(self) -> bool:
        """Check if mock capture is active"""
        return self._is_capturing

    def get_capture_duration(self) -> float:
        """
        Get simulated capture duration.

        If simulate_timing=True, returns real elapsed time.
        If simulate_timing=False, returns target duration immediately.
        """
        if not self._is_capturing or self._start_time is None:
            return 0.0

        if self.simulate_timing:
            # Real-time duration
            return time.time() - self._start_time
        else:
            # Instant duration (for fast tests)
            return self._target_duration or 0.0

    def get_output_file(self) -> Optional[Path]:
        """Get current output file"""
        return self._output_file

    def check_health(self) -> dict:
        """
        Return mock health information.

        Can be configured to simulate unhealthy states for testing.
        """
        # Default health values
        health = {
            'is_healthy': self._is_healthy and self._is_capturing,
            'error_message': self._error_message,
            'frames_captured': self._simulated_frames,
            'fps': 30.0,
            'file_size_mb': 0.0,
        }

        # If not capturing, mark as unhealthy
        if not self._is_capturing:
            health['is_healthy'] = False
            if not health['error_message']:
                health['error_message'] = "Capture not running"

        # Calculate simulated file size if capturing
        if self._is_capturing and self._output_file and self._output_file.exists():
            duration = self.get_capture_duration()
            health['file_size_mb'] = duration * 4.0  # 4 MB per second

        return health

    def is_available(self) -> bool:
        """Mock capture is always available"""
        return True

    def cleanup(self) -> None:
        """Stop capture and clean up"""
        self.logger.debug("[MOCK] Cleanup")

        if self._is_capturing:
            self.stop_capture()

    # =========================================================================
    # TESTING HELPER METHODS (not part of VideoCaptureInterface)
    # =========================================================================
    # These methods are ONLY for testing - configure mock behavior

    def simulate_start_failure(self) -> None:
        """
        Configure mock to fail on next start_capture() call.

        Used to test error handling in tests.

        Example:
            mock.simulate_start_failure()
            with pytest.raises(CaptureError):
                mock.start_capture(Path("test.mp4"))
        """
        self._should_fail_start = True
        self.logger.debug("[MOCK] Configured to fail on start")

    def simulate_crash_during_capture(self, after_seconds: float = 5.0) -> None:
        """
        Configure mock to crash during capture.

        Used to test error recovery in tests.

        Args:
            after_seconds: Crash after this many seconds

        Example:
            mock.simulate_crash_during_capture(after_seconds=2.0)
            mock.start_capture(Path("test.mp4"), duration=10)
            time.sleep(3)
            assert not mock.check_health()['is_healthy']
        """
        self._should_crash_during = True
        self._crash_after_seconds = after_seconds
        self.logger.debug(f"[MOCK] Configured to crash after {after_seconds}s")

    def reset_test_config(self) -> None:
        """
        Reset test configuration to normal operation.

        Call between tests to reset failure scenarios.
        """
        self._should_fail_start = False
        self._should_crash_during = False
        self._crash_after_seconds = None
        self._is_healthy = True
        self._error_message = None
        self._crashed = False
        self.logger.debug("[MOCK] Test configuration reset")

    def get_simulated_frames(self) -> int:
        """
        Get number of simulated frames captured.

        Useful for verifying capture is actually running.

        Returns:
            Number of frames simulated
        """
        return self._simulated_frames

    def __del__(self):
        """Destructor - ensure cleanup"""
        self.cleanup()
