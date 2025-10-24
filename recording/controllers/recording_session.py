"""
Recording Session

Manages a single recording session with duration tracking, extensions, and warnings.
Coordinates camera, timing, and callbacks for state changes.

This is the high-level controller that your main service will use.

SOLID Principles:
- Single Responsibility: Only manages recording session lifecycle
- Open/Closed: Easy to add callbacks for different events
- Dependency Inversion: Depends on CameraManager interface
"""

import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from recording.constants import (
    DEFAULT_RECORDING_DURATION,
    EXTENSION_DURATION,
    MAX_RECORDING_DURATION,
    WARNING_TIME,
    RecordingState,
    format_duration,
)
from recording.controllers.camera_manager import CameraManager


class RecordingSession:
    """
    Manages a single recording session.

    Features:
    - Duration tracking (10min default)
    - Extensions (+5min, max 25min total)
    - Warning at 1 minute remaining
    - Callbacks for state changes
    - Auto-stop at duration limit

    Usage:
        session = RecordingSession(camera_manager)

        # Register callbacks
        session.on_warning = lambda: print("1 minute remaining!")
        session.on_complete = lambda: print("Recording complete")

        # Start recording
        session.start(output_file, duration=600)

        # During recording, can extend
        if session.extend():
            print("Extended by 5 minutes")

        # Stop when done
        session.stop()
    """

    def __init__(self, camera_manager: CameraManager):
        """
        Initialize recording session.

        Args:
            camera_manager: Camera manager for video capture

        Example:
            camera = CameraManager()
            session = RecordingSession(camera)
        """
        self.logger = logging.getLogger(__name__)
        self.camera = camera_manager

        # Session state
        self.state = RecordingState.IDLE
        self._output_file: Optional[Path] = None
        self._start_time: Optional[float] = None
        self._initial_duration: float = DEFAULT_RECORDING_DURATION
        self._current_duration_limit: float = DEFAULT_RECORDING_DURATION
        self._extension_count: int = 0

        # Warning/completion tracking
        self._warning_issued = False
        self._completed = False

        # Monitoring thread
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_stop_event = threading.Event()

        # Callbacks for events
        # These are called when specific events occur
        self.on_start: Optional[Callable[[], None]] = None
        self.on_warning: Optional[Callable[[], None]] = None
        self.on_complete: Optional[Callable[[], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_extension: Optional[Callable[[int], None]] = None

        self.logger.info("Recording Session initialized")

    def start(
        self,
        output_file: Path,
        duration: float = DEFAULT_RECORDING_DURATION,
    ) -> bool:
        """
        Start recording session.

        Args:
            output_file: Path where video will be saved
            duration: Initial recording duration in seconds

        Returns:
            True if started successfully, False otherwise

        Example:
            session.start(Path("/recordings/video.mp4"), duration=600)
        """
        # Check if already recording
        if self.state != RecordingState.IDLE:
            self.logger.error(f"Cannot start - session in state: {self.state.value}")
            return False

        # Validate duration
        if duration <= 0 or duration > MAX_RECORDING_DURATION:
            self.logger.error(
                f"Invalid duration: {duration}s "
                f"(must be 1-{MAX_RECORDING_DURATION})",
            )
            return False

        self.logger.info(
            f"Starting recording session: {output_file.name} "
            f"({format_duration(duration)})",
        )

        # Update state
        self.state = RecordingState.STARTING
        self._output_file = output_file
        self._initial_duration = duration
        self._current_duration_limit = duration
        self._extension_count = 0
        self._warning_issued = False
        self._completed = False

        try:
            # Start camera recording
            success = self.camera.start_recording(
                output_file,
                duration=None,
            )  # We manage duration

            if not success:
                self.logger.error("Failed to start camera recording")
                self.state = RecordingState.ERROR
                self._trigger_error_callback("Failed to start camera")
                return False

            # Record start time
            self._start_time = time.time()

            # Update state
            self.state = RecordingState.RECORDING

            # Start monitoring thread
            self._start_monitoring()

            # Trigger callback
            self._trigger_start_callback()

            self.logger.info("Recording session started successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error starting session: {e}", exc_info=True)
            self.state = RecordingState.ERROR
            self._trigger_error_callback(str(e))
            return False

    def stop(self) -> bool:
        """
        Stop recording session.

        Returns:
            True if stopped successfully, False if not recording

        Example:
            session.stop()
        """
        if self.state not in [RecordingState.RECORDING, RecordingState.STARTING]:
            self.logger.warning(
                f"Cannot stop - not recording (state: {self.state.value})",
            )
            return False

        self.logger.info("Stopping recording session...")

        # Update state
        self.state = RecordingState.STOPPING

        # Stop monitoring
        self._stop_monitoring()

        try:
            # Stop camera
            success = self.camera.stop_recording()

            if success:
                self.logger.info("Recording session stopped successfully")
                self.state = RecordingState.IDLE

                # Trigger completion callback if not already triggered
                if not self._completed:
                    self._completed = True
                    self._trigger_complete_callback()

                return True
            self.logger.warning("Camera stop returned failure")
            self.state = RecordingState.IDLE
            return False

        except Exception as e:
            self.logger.error(f"Error stopping session: {e}")
            self.state = RecordingState.ERROR
            self._trigger_error_callback(str(e))
            return False

    def extend(self) -> bool:
        """
        Extend recording by EXTENSION_DURATION seconds.

        Can extend up to MAX_RECORDING_DURATION total.

        Returns:
            True if extended, False if at maximum or not recording

        Example:
            if session.extend():
                print("Extended by 5 minutes")
            else:
                print("Cannot extend - at maximum")
        """
        if self.state != RecordingState.RECORDING:
            self.logger.warning(
                f"Cannot extend - not recording (state: {self.state.value})",
            )
            return False

        # Check if already at maximum
        new_limit = self._current_duration_limit + EXTENSION_DURATION
        if new_limit > MAX_RECORDING_DURATION:
            self.logger.warning(
                f"Cannot extend - would exceed maximum "
                f"({new_limit}s > {MAX_RECORDING_DURATION}s)",
            )
            return False

        # Extend duration
        self._current_duration_limit = new_limit
        self._extension_count += 1

        # Reset warning flag (may need to warn again)
        self._warning_issued = False

        self.logger.info(
            f"Recording extended to {format_duration(new_limit)} "
            f"(extension #{self._extension_count})",
        )

        # Trigger callback
        self._trigger_extension_callback(self._extension_count)

        return True

    def get_elapsed_time(self) -> float:
        """
        Get elapsed recording time in seconds.

        Returns:
            Seconds since recording started, or 0.0 if not recording
        """
        if self.state != RecordingState.RECORDING or self._start_time is None:
            return 0.0

        return time.time() - self._start_time

    def get_remaining_time(self) -> float:
        """
        Get remaining recording time in seconds.

        Returns:
            Seconds until recording stops, or 0.0 if not recording
        """
        if self.state != RecordingState.RECORDING:
            return 0.0

        elapsed = self.get_elapsed_time()
        remaining = self._current_duration_limit - elapsed
        return max(0.0, remaining)

    def get_duration_limit(self) -> float:
        """
        Get current duration limit in seconds.

        This increases when extended.

        Returns:
            Current duration limit
        """
        return self._current_duration_limit

    def can_extend(self) -> bool:
        """
        Check if recording can be extended.

        Returns:
            True if extension is possible, False otherwise
        """
        if self.state != RecordingState.RECORDING:
            return False

        new_limit = self._current_duration_limit + EXTENSION_DURATION
        return new_limit <= MAX_RECORDING_DURATION

    def _start_monitoring(self) -> None:
        """
        Start background monitoring thread.

        Monitors recording progress and triggers warnings/auto-stop.
        """
        self._monitor_stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_worker,
            daemon=True,
            name="RecordingMonitor",
        )
        self._monitor_thread.start()
        self.logger.debug("Monitoring thread started")

    def _stop_monitoring(self) -> None:
        """Stop monitoring thread"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_stop_event.set()
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None
            self.logger.debug("Monitoring thread stopped")

    def _monitor_worker(self) -> None:
        """
        Background thread that monitors recording progress.

        Responsibilities:
        - Check remaining time
        - Trigger warning at WARNING_TIME remaining
        - Auto-stop when duration limit reached
        - Monitor camera health
        """
        check_interval = 0.1  # Check every 100ms for responsiveness

        while not self._monitor_stop_event.wait(check_interval):
            if self.state != RecordingState.RECORDING:
                break

            try:
                remaining = self.get_remaining_time()

                # Check for warning time
                if (
                    not self._warning_issued
                    and remaining <= WARNING_TIME
                    and remaining > 0
                ):
                    self.logger.info(
                        f"Warning: {format_duration(remaining)} remaining",
                    )
                    self._warning_issued = True
                    self._trigger_warning_callback()

                # Check for auto-stop
                if remaining <= 0:
                    self.logger.info("Duration limit reached, auto-stopping")

                    # Stop monitoring thread first
                    # (we're in it, so just signal and exit)
                    self._monitor_stop_event.set()

                    # Update state
                    self.state = RecordingState.STOPPING

                    # Stop camera
                    try:
                        self.camera.stop_recording()
                    except Exception as e:
                        self.logger.error(f"Error stopping camera: {e}")

                    self.state = RecordingState.IDLE

                    # Trigger completion callback
                    if not self._completed:
                        self._completed = True
                        self._trigger_complete_callback()

                    break  # Exit monitoring loop

                # Check camera health every 5 seconds
                elapsed = self.get_elapsed_time()
                # Check every 5 seconds (50 * 0.1s)
                if int(elapsed * 10) % 50 == 0 and elapsed > 0:
                    health = self.camera.check_health()
                    if not health["is_healthy"]:
                        self.logger.error(
                            f"Camera health check failed: {health['error_message']}",
                        )
                        if health.get("critical", False):
                            self.logger.error("Critical camera error, stopping")
                            self.state = RecordingState.ERROR
                            self._trigger_error_callback(health["error_message"])
                            self.stop()
                            break

            except Exception as e:
                self.logger.error(f"Error in monitoring thread: {e}")

    # =========================================================================
    # CALLBACK TRIGGERS
    # =========================================================================

    def _trigger_start_callback(self) -> None:
        """Trigger on_start callback"""
        if self.on_start:
            try:
                self.on_start()
            except Exception as e:
                self.logger.error(f"Error in start callback: {e}")

    def _trigger_warning_callback(self) -> None:
        """Trigger on_warning callback"""
        if self.on_warning:
            try:
                self.on_warning()
            except Exception as e:
                self.logger.error(f"Error in warning callback: {e}")

    def _trigger_complete_callback(self) -> None:
        """Trigger on_complete callback"""
        if self.on_complete:
            try:
                self.on_complete()
            except Exception as e:
                self.logger.error(f"Error in complete callback: {e}")

    def _trigger_error_callback(self, error_message: str) -> None:
        """Trigger on_error callback"""
        if self.on_error:
            try:
                self.on_error(error_message)
            except Exception as e:
                self.logger.error(f"Error in error callback: {e}")

    def _trigger_extension_callback(self, extension_count: int) -> None:
        """Trigger on_extension callback"""
        if self.on_extension:
            try:
                self.on_extension(extension_count)
            except Exception as e:
                self.logger.error(f"Error in extension callback: {e}")

    # =========================================================================
    # STATUS AND INFO
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """
        Get complete session status.

        Returns:
            Dictionary with status information
        """
        return {
            "state": self.state.value,
            "output_file": str(self._output_file) if self._output_file else None,
            "elapsed_time": self.get_elapsed_time(),
            "remaining_time": self.get_remaining_time(),
            "duration_limit": self._current_duration_limit,
            "initial_duration": self._initial_duration,
            "extension_count": self._extension_count,
            "can_extend": self.can_extend(),
            "warning_issued": self._warning_issued,
        }

    def get_session_info(self) -> str:
        """
        Get human-readable session information.

        Returns:
            Formatted string with session details
        """
        if self.state == RecordingState.IDLE:
            return "No active recording session"

        status = self.get_status()

        info = [
            f"State: {status['state']}",
            f"File: {status['output_file']}",
            f"Elapsed: {format_duration(status['elapsed_time'])}",
            f"Remaining: {format_duration(status['remaining_time'])}",
            f"Extensions: {status['extension_count']}",
        ]

        if status["can_extend"]:
            info.append("Can extend: Yes")
        else:
            info.append("Can extend: No (at maximum)")

        return "\n".join(info)

    def cleanup(self) -> None:
        """
        Stop session and clean up resources.

        Always call this when done with session!
        """
        self.logger.info("Cleaning up Recording Session")

        # Stop monitoring
        self._stop_monitoring()

        # Stop recording if active
        if self.state in [RecordingState.RECORDING, RecordingState.STARTING]:
            self.stop()

        self.logger.info("Recording Session cleanup complete")

    def __del__(self):
        """Destructor - ensure cleanup"""
        self.cleanup()
