"""
Recorder Service

Main service coordinator for the video recording system.
This is the central orchestrator that wires all controllers together.

Architecture:
- Simple state tracking (no over-engineering)
- Direct controller coordination (no event bus abstraction)
- Background upload queue (one at a time, oldest first)
- Background cleanup worker (automatic, hourly)
- Silent operation (no audio feedback)

State Flow:
    BOOTING → READY → RECORDING → PROCESSING → READY
                ↑                       ↓           ↑
                |                  (save to storage)|
                +------------ ERROR (with recovery)-+

Button Logic:
- READY: Short or long press = start recording
- RECORDING: Short press = stop, Long press = extend (+5min)
- PROCESSING: Brief state while saving (2-3 seconds), button disabled
- ERROR: Short or long press = attempt recovery

Upload Queue:
- Runs in background thread
- Processes pending videos (oldest first)
- One upload at a time
- Can run during new recordings
- Auto-retry on failure (wait 5min, retry when idle)
- Silent on success, logs failures
"""

import json
import logging
import logging.handlers
import os
import queue
import signal
import sys
import threading
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from config.settings import (
    CLEANUP_INTERVAL_SECONDS,
    CONTROL_FILE,
    DEFAULT_RECORDING_DURATION,
    EXTENSION_DURATION,
    HEARTBEAT_FILE,
    HEARTBEAT_INTERVAL,
    MAX_UPLOAD_RETRIES,
    NETWORK_CHECK_INTERVAL,
    RESTART_COUNTER_FILE,
    RETRY_DELAY_SECONDS,
    STORAGE_BASE_PATH,
    WARNING_TIME,
    YOUTUBE_PLAYLIST_ID,
)
from core.network import check_internet_connectivity
from hardware import ButtonController, LEDController
from hardware.constants import LEDPattern
from recording import CameraManager, RecordingSession, generate_filename
from storage import StorageController, VideoFile
from upload import UploadController


class SystemState(Enum):
    """System states - simple enum, no complex state machine needed."""

    BOOTING = "booting"
    READY = "ready"
    RECORDING = "recording"
    PROCESSING = "processing"  # Brief state while saving to storage
    ERROR = "error"


class ButtonPress(Enum):
    """Button press types detected by ButtonController."""

    SHORT = "short"
    LONG = "long"


class RecorderService:
    """
    Main service coordinator.

    Wires together:
    - Hardware controllers (button, LEDs)
    - Recording system (camera, session)
    - Storage and upload
    - State management and error recovery
    - Background workers (upload queue, cleanup)

    Usage:
        service = RecorderService()
        service.run()  # Blocks until shutdown
    """

    def __init__(self):
        """Initialize all controllers and setup callbacks."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Recorder Service...")

        # State tracking
        self.state = SystemState.BOOTING
        self.state_start_time = time.time()
        self.running = False
        self.error_count = 0  # Track total errors (red LED activations)

        # Restart counter (persistent across service restarts)
        self.restart_counter_file = Path(RESTART_COUNTER_FILE)
        self.restart_count = self._increment_restart_counter()

        # Heartbeat setup for liveness monitoring
        self.heartbeat_file = Path(HEARTBEAT_FILE)
        self.last_heartbeat = time.time()

        # Remote control file for SSH/script commands
        self.control_file = Path(CONTROL_FILE)

        # Recording session tracking
        self.current_session: Optional[RecordingSession] = None
        self.current_output_file: Optional[Path] = None
        self.session_start_time: Optional[float] = None

        # Upload queue management
        self.upload_queue: queue.Queue = queue.Queue()
        self.upload_worker_thread: Optional[threading.Thread] = None
        self.currently_uploading: Optional[VideoFile] = None
        self.upload_lock = threading.Lock()

        # Cleanup worker
        self.cleanup_worker_thread: Optional[threading.Thread] = None
        self.last_cleanup_time = time.time()

        # Network monitoring worker
        self.network_monitor_thread: Optional[threading.Thread] = None
        self.internet_connected = False  # Track internet connectivity status

        # Initialize hardware controllers
        self.logger.info("Initializing hardware controllers...")
        self.led = LEDController()
        self.button = ButtonController()

        # Initialize recording system
        self.logger.info("Initializing recording system...")
        self.camera = CameraManager()

        # Initialize storage and upload
        self.logger.info("Initializing storage and upload...")
        self.storage = StorageController()
        self.uploader = UploadController(playlist_id=YOUTUBE_PLAYLIST_ID)

        # Wire up callbacks
        self._setup_callbacks()

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        self.logger.info("Recorder Service initialized successfully")

    def _setup_callbacks(self):
        """Wire up all controller callbacks for event coordination."""
        # Button callback - handle all button presses
        self.button.register_callback(self._handle_button_press)

        # Storage callbacks - handle disk issues
        self.storage.on_disk_full = self._handle_disk_full
        self.storage.on_low_space = self._handle_low_space
        self.storage.on_storage_error = self._handle_storage_error

        # Recording session callbacks will be set when session starts
        # (on_warning, on_complete callbacks)

    def run(self):
        """
        Main service loop.

        Runs until shutdown signal received.
        Monitors recording state, handles warnings, coordinates uploads.
        """
        self.running = True
        self.logger.info("Starting Recorder Service main loop...")

        # Start background workers
        self._start_upload_worker()
        self._start_cleanup_worker()
        self._start_network_monitor()

        # Transition from BOOTING to READY
        self._transition_to_ready()

        # Main loop - 10Hz update rate
        try:
            while self.running:
                self._update_loop()
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        finally:
            self._shutdown()

    def _update_loop(self):
        """
        Main update loop - called 10 times per second.

        Monitors:
        - Recording session status
        - Upload queue
        - Error conditions
        """
        # Write heartbeat for liveness monitoring
        current_time = time.time()
        if current_time - self.last_heartbeat >= HEARTBEAT_INTERVAL:
            self._write_heartbeat()
            self.last_heartbeat = current_time

        # Check for remote control commands (SSH/script control)
        self._check_control_commands()

        # If recording, check session health
        if self.state == SystemState.RECORDING and self.current_session:
            # RecordingSession handles its own timing and warnings
            # We just need to check if camera is still healthy
            if not self.camera.is_recording():
                self.logger.error("Camera stopped unexpectedly!")
                self._handle_recording_error("Camera stopped unexpectedly")

    def _increment_restart_counter(self) -> int:
        """
        Increment and persist restart counter.

        Reads current count from file, increments it, writes back.
        This survives service restarts to track total restart count.

        Returns:
            New restart count (int)
        """
        try:
            # Read current count (default to 0 if file doesn't exist)
            if self.restart_counter_file.exists():
                current_count = int(self.restart_counter_file.read_text().strip())
            else:
                current_count = 0

            # Increment and save
            new_count = current_count + 1
            self.restart_counter_file.write_text(str(new_count))
            self.logger.info(f"Service restart #{new_count}")
            return new_count

        except Exception as e:
            self.logger.error(f"Failed to update restart counter: {e}")
            return 0  # Default to 0 on error

    def _write_heartbeat(self):
        """
        Write heartbeat for liveness detection.

        Creates a JSON file with current system state that external
        watchdog can monitor. Atomic write prevents partial reads.

        Heartbeat data includes:
        - timestamp: Current time (ISO format)
        - uptime_seconds: Time since service started
        - state: Current system state (booting/ready/recording/etc)
        - recording_active: Whether currently recording
        - upload_queue_size: Number of videos waiting to upload
        - currently_uploading: Filename being uploaded (if any)
        - pid: Process ID for monitoring
        - error_count: Total errors since service start
        - restart_count: Total service restarts (persistent)
        - internet_connected: Whether internet is currently available
        """
        try:
            heartbeat = {
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": time.time() - self.state_start_time,
                "state": self.state.value,
                "recording_active": self.current_session is not None,
                "upload_queue_size": self.upload_queue.qsize(),
                "currently_uploading": (
                    self.currently_uploading.filename
                    if self.currently_uploading
                    else None
                ),
                "pid": os.getpid(),
                "error_count": self.error_count,
                "restart_count": self.restart_count,
                "internet_connected": self.internet_connected,
            }

            # Atomic write (write to temp file, then rename)
            # This prevents watchdog from reading partial/corrupted JSON
            tmp_file = self.heartbeat_file.with_suffix(".tmp")
            tmp_file.write_text(json.dumps(heartbeat, indent=2))
            tmp_file.rename(self.heartbeat_file)

        except Exception as e:
            # Never crash on heartbeat failure - just log and continue
            # Heartbeat is for monitoring, not critical functionality
            self.logger.warning(f"Failed to write heartbeat: {e}")

    def _check_control_commands(self):
        """
        Check for and process remote control commands.

        Monitors control file for commands sent via SSH/scripts.
        File-based approach: cheap to check (tmpfs), flexible, simple.

        Supported commands:
        - START: Start recording (like short button press in READY state)
        - STOP: Stop recording (like short button press in RECORDING state)
        - EXTEND: Extend recording by 5 minutes (like long press in
          RECORDING)
        - STATUS: Log current state (for debugging)

        WHY file-based control instead of signals or sockets:
        - Simple: echo "START" > /tmp/recorder_control.cmd
        - No parsing overhead (just read small text file)
        - Testable: can manually create file to test
        - tmpfs = RAM-backed, no disk I/O
        - Self-cleaning: file deleted after processing

        Performance impact: Negligible (~1µs Path.exists() check per loop)
        """
        if not self.control_file.exists():
            return  # No command waiting - most common case

        try:
            # Read command from file
            command = self.control_file.read_text().strip().upper()

            # Delete file immediately to prevent re-processing
            self.control_file.unlink()

            self.logger.info(f"Remote command received: {command}")

            # Process command using helper method
            self._process_remote_command(command)

        except Exception as e:
            # Never crash on control command failure
            self.logger.error(f"Failed to process control command: {e}")
            # Try to clean up the file even if processing failed
            try:
                if self.control_file.exists():
                    self.control_file.unlink()
            except Exception:  # noqa: S110
                # Silently ignore cleanup failures - already in error path
                # Main error already logged above
                pass

    def _process_remote_command(self, command: str):
        """
        Process a specific remote command.

        Separated from _check_control_commands to reduce complexity.

        Args:
            command: Command string (START, STOP, EXTEND, STATUS)
        """
        if command == "START":
            if self.state == SystemState.READY:
                self.logger.info("Remote START → starting recording")
                self._start_recording()
            else:
                self.logger.warning(
                    f"Remote START ignored - state is {self.state.value} "
                    "(must be READY)",
                )

        elif command == "STOP":
            if self.state == SystemState.RECORDING:
                self.logger.info("Remote STOP → stopping recording")
                self._stop_recording()
            else:
                self.logger.warning(
                    f"Remote STOP ignored - state is {self.state.value} "
                    "(must be RECORDING)",
                )

        elif command == "EXTEND":
            if self.state == SystemState.RECORDING:
                self.logger.info("Remote EXTEND → extending recording")
                self._extend_recording()
            else:
                self.logger.warning(
                    f"Remote EXTEND ignored - state is {self.state.value} "
                    "(must be RECORDING)",
                )

        elif command == "STATUS":
            self.logger.info(
                f"Remote STATUS → state: {self.state.value}, "
                f"recording: {self.current_session is not None}, "
                f"queue: {self.upload_queue.qsize()}",
            )

        else:
            self.logger.warning(f"Unknown remote command: {command}")

    # =========================================================================
    # STATE TRANSITIONS
    # =========================================================================

    def _transition_to_ready(self):
        """
        Transition to READY state.

        Updates LED to green, enables button.
        Silent operation - no audio.
        """
        self.logger.info("Transitioning to READY state")
        self.state = SystemState.READY
        self.state_start_time = time.time()

        # Update LED status (silent - no audio)
        self.led.set_status(LEDPattern.READY)

        self.logger.info("System READY for recording")

    def _transition_to_recording(self):
        """Start recording session."""
        self.logger.info("Transitioning to RECORDING state")
        self.state = SystemState.RECORDING
        self.state_start_time = time.time()

        # Update LED to recording (blinking green)
        self.led.set_status(LEDPattern.RECORDING)

    def _transition_to_processing(self):
        """
        Transition to PROCESSING state (saving to storage).

        This is a BRIEF state (2-3 seconds) while:
        - Stopping FFmpeg
        - Moving file to storage
        - Saving metadata to database
        - Validating video

        Then immediately back to READY.
        """
        self.logger.info("Transitioning to PROCESSING state")
        self.state = SystemState.PROCESSING
        self.state_start_time = time.time()

        # Update LED to orange (brief busy indicator)
        self.led.set_status(LEDPattern.PROCESSING)

    def _transition_to_error(self, error_message: str):
        """
        Transition to ERROR state.

        Args:
            error_message: Description of error for logging
        """
        self.logger.error(f"Transitioning to ERROR state: {error_message}")
        self.error_count += 1  # Increment error counter for metrics
        self.state = SystemState.ERROR
        self.state_start_time = time.time()

        # Update hardware - red LED (silent - no audio)
        self.led.set_status(LEDPattern.ERROR)

    # =========================================================================
    # BUTTON PRESS HANDLING
    # =========================================================================

    def _handle_button_press(self, press_type: str):
        """
        Handle button press based on current state.

        Called by ButtonController when button pressed.

        Args:
            press_type: "short" or "long"
        """
        press = ButtonPress.SHORT if press_type == "short" else ButtonPress.LONG
        self.logger.info(f"Button press: {press_type} in state {self.state.value}")

        # Delegate to state-specific handlers
        if self.state == SystemState.READY:
            self._handle_button_ready(press)
        elif self.state == SystemState.RECORDING:
            self._handle_button_recording(press)
        elif self.state == SystemState.PROCESSING:
            self._handle_button_processing(press)
        elif self.state == SystemState.ERROR:
            self._handle_button_error(press)

    def _handle_button_ready(self, press: ButtonPress):
        """
        Handle button in READY state.

        Short or long press: Start recording (both trigger same action)
        """
        # Both short and long press start recording in READY state
        self.logger.debug(f"{press.value} press in READY → start recording")
        self._start_recording()

    def _handle_button_recording(self, press: ButtonPress):
        """
        Handle button in RECORDING state.

        Short press: Stop recording
        Long press: Extend recording by 5 minutes
        """
        if press == ButtonPress.SHORT:
            self._stop_recording()
        elif press == ButtonPress.LONG:
            self._extend_recording()

    def _handle_button_processing(self, press: ButtonPress):
        """
        Handle button in PROCESSING state.

        All presses ignored - must wait for storage save to complete.
        This is very brief (2-3 seconds).
        """
        self.logger.debug(f"{press.value} press ignored in PROCESSING state (busy)")

    def _handle_button_error(self, press: ButtonPress):
        """
        Handle button in ERROR state.

        Short or long press: Attempt recovery (both trigger same action)
        """
        # Both short and long press attempt recovery in ERROR state
        self.logger.debug(f"{press.value} press in ERROR → attempt recovery")
        self._attempt_recovery()

    # =========================================================================
    # RECORDING OPERATIONS
    # =========================================================================

    def _start_recording(self):
        """
        Start a new recording session.

        Steps:
        1. Check storage space
        2. Generate output filename
        3. Create recording session
        4. Start camera
        5. Transition to RECORDING state
        """
        self.logger.info("Starting new recording session")

        # Check storage space
        if not self.storage.check_space():
            self.logger.error("Insufficient storage space!")
            self._handle_disk_full()
            return

        # Check camera is ready
        if not self.camera.is_ready():
            self.logger.error("Camera not ready!")
            self._transition_to_error("Camera not available")
            return

        # Generate output filename with timestamp (includes milliseconds)
        pending_dir = STORAGE_BASE_PATH / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        self.current_output_file = generate_filename(pending_dir, extension="mp4")

        # Create recording session
        self.current_session = RecordingSession(camera_manager=self.camera)

        # Setup session callbacks (silent - no audio warning)
        self.current_session.on_warning = (
            self._handle_recording_warning
        )  # Just log, no audio
        self.current_session.on_complete = self._handle_recording_complete

        # Start recording
        success = self.current_session.start(
            output_file=self.current_output_file,
            duration=DEFAULT_RECORDING_DURATION,
        )

        if not success:
            self.logger.error("Failed to start recording session")
            self._transition_to_error("Failed to start recording")
            self.current_session = None
            self.current_output_file = None
            return

        # Success - transition to RECORDING
        self.session_start_time = time.time()
        self._transition_to_recording()

        self.logger.info(f"Recording started: {self.current_output_file.name}")

    def _stop_recording(self):
        """
        Stop current recording session.

        Steps:
        1. Transition to PROCESSING (orange LED)
        2. Stop recording session
        3. Save to storage (2-3 seconds)
        4. Queue upload in background
        5. Transition to READY immediately
        """
        if not self.current_session:
            self.logger.warning("No active session to stop")
            return

        self.logger.info("Stopping recording session")

        # Save references before clearing (prevent race condition)
        session = self.current_session
        output_file = self.current_output_file
        start_time = self.session_start_time

        # Clear session references IMMEDIATELY to prevent double-stop
        # This must happen BEFORE stopping the session to prevent
        # the on_complete callback from re-entering this function
        self.current_session = None
        self.current_output_file = None
        self.session_start_time = None

        # Transition to PROCESSING first (orange LED while saving)
        self._transition_to_processing()

        # Stop the session
        session.stop()
        session.cleanup()  # Clean up monitoring thread and resources

        # Calculate recording duration
        duration = time.time() - start_time if start_time else 0

        # Save to storage (this takes 2-3 seconds)
        try:
            video = self.storage.save_recording(
                video_path=output_file,
                duration_seconds=int(duration),
            )
            self.logger.info(f"Recording saved to storage: {video.filename}")

            # Upload will be picked up automatically by the upload worker
            # which checks storage.get_pending_uploads() continuously
            # No need to queue here - prevents double upload attempts

        except Exception as e:
            self.logger.error(f"Failed to save recording: {e}")
            self._transition_to_error(f"Storage error: {e}")
            return

        # Immediately back to READY (green LED)
        # Upload happens in background, invisible to user
        self._transition_to_ready()

    def _extend_recording(self):
        """
        Extend current recording by 5 minutes.

        Called when user double-presses button during recording.
        Silent operation - no audio feedback.
        """
        if not self.current_session:
            self.logger.warning("No active session to extend")
            return

        self.logger.info("Extending recording session")

        # Extend the session
        success = self.current_session.extend()

        if success:
            extension_minutes = EXTENSION_DURATION // 60
            extension_seconds = EXTENSION_DURATION % 60
            if extension_seconds > 0:
                time_str = f"{extension_minutes}:{extension_seconds:02d}"
                self.logger.info(f"Recording extended by {time_str}")
            else:
                self.logger.info(f"Recording extended by {extension_minutes} minutes")

            # Restore LED to recording pattern (no longer in warning zone)
            self.led.set_status(LEDPattern.RECORDING)

            # Flash green 5x quickly to confirm extension success
            self.led.flash_extension_success()
        else:
            self.logger.warning("Failed to extend recording (max duration reached?)")

    def _handle_recording_warning(self):
        """
        Handle recording warning from recording session.

        Called by RecordingSession when WARNING_TIME seconds remaining.
        Triggers LED warning sequence (green-orange-red animation).
        """
        warning_minutes = WARNING_TIME // 60
        warning_seconds = WARNING_TIME % 60
        if warning_minutes > 0 and warning_seconds > 0:
            time_remaining = f"{warning_minutes}:{warning_seconds:02d}"
        elif warning_minutes > 0:
            time_remaining = f"{warning_minutes} minute(s)"
        else:
            time_remaining = f"{warning_seconds} seconds"
        self.logger.info(f"Recording warning: {time_remaining} remaining")

        # Flash LED warning sequence (green-orange-red)
        self.led.play_warning_sequence()

    def _handle_recording_complete(self):
        """
        Handle automatic recording completion.

        Called by RecordingSession when duration limit reached.
        Same as manual stop.
        """
        self.logger.info("Recording completed automatically (duration limit)")
        self._stop_recording()

    def _handle_recording_error(self, error_message: str):
        """
        Handle recording error.

        Args:
            error_message: Description of error
        """
        self.logger.error(f"Recording error: {error_message}")

        # Stop session if active
        if self.current_session:
            self.current_session.stop()
            self.current_session.cleanup()  # Clean up monitoring thread
            self.current_session = None

        # Clean up
        self.current_output_file = None
        self.session_start_time = None

        # Transition to error state
        self._transition_to_error(error_message)

    # =========================================================================
    # UPLOAD QUEUE OPERATIONS
    # =========================================================================

    def _start_upload_worker(self):
        """Start background upload queue worker thread."""
        self.logger.info("Starting upload queue worker...")
        self.upload_worker_thread = threading.Thread(
            target=self._upload_worker,
            daemon=True,
            name="UploadWorker",
        )
        self.upload_worker_thread.start()

    def _queue_upload(self, video: VideoFile):
        """
        Queue video upload in background.

        Args:
            video: VideoFile object to upload
        """
        self.logger.info(f"Queueing upload for: {video.filename}")
        self.upload_queue.put(video)

    def _upload_worker(self):
        """
        Background worker for processing upload queue.

        Runs continuously:
        - Processes pending uploads from storage
        - Processes newly queued uploads
        - One upload at a time (oldest first)
        - Auto-retry on failure
        - Silent on success, logs failures
        """
        self.logger.info("Upload worker thread started")

        while self.running:
            try:
                # First, check for pending uploads from storage
                # (videos that were saved but not yet uploaded)
                pending = self.storage.get_pending_uploads()
                for video in pending:
                    if not self.running:
                        break
                    self._process_upload(video)

                # Then process newly queued uploads
                try:
                    video = self.upload_queue.get(timeout=1.0)
                    self._process_upload(video)
                except queue.Empty:
                    # No uploads in queue, wait and check again
                    continue

            except Exception as e:
                self.logger.error(f"Upload worker error: {e}", exc_info=True)
                time.sleep(5)  # Brief pause before retry

        self.logger.info("Upload worker thread stopped")

    def _process_upload(self, video: VideoFile):
        """
        Process a single video upload.

        Coordinates storage, upload status, and LED feedback:
        - Marks upload started in database
        - Activates BLUE LED (blinks during upload)
        - Uploads to YouTube with automatic retry on failure
        - Marks upload success/failed in database
        - Always deactivates BLUE LED in finally block

        Args:
            video: VideoFile to upload

        LED Behavior:
            - BLUE LED blinks continuously while upload is in progress
            - BLUE LED turns off immediately when upload completes (success/failure)
            - Blinking at 0.5s interval (on 0.25s, off 0.25s)
        """
        with self.upload_lock:
            self.currently_uploading = video

        try:
            self.logger.info(f"Starting upload: {video.filename}")

            # Mark upload started and activate BLUE LED
            self.storage.mark_upload_started(video)
            self.led.set_upload_active(True)

            # Generate timestamp for video title
            timestamp = video.created_at.strftime("%Y-%m-%d %H:%M:%S")

            # Upload video
            result = self.uploader.upload_video(
                video_path=str(video.filepath),
                timestamp=timestamp,
            )

            if result.success:
                video_url = f"https://www.youtube.com/watch?v={result.video_id}"
                self.logger.info(
                    f"Upload successful: {video.filename} → {video_url}",
                )

                # Mark as uploaded in storage
                self.storage.mark_upload_success(video, video_url)

                # Silent on success - no audio feedback

            else:
                # Upload failed
                error_msg = result.error_message or "Unknown error"
                self.logger.error(f"Upload failed: {video.filename} - {error_msg}")

                # Mark as failed in storage
                self.storage.mark_upload_failed(video, error_msg)

                # Check if we should retry
                if video.upload_attempts < MAX_UPLOAD_RETRIES:
                    self.logger.info(
                        f"Will retry upload after {RETRY_DELAY_SECONDS}s "
                        f"(attempt {video.upload_attempts + 1}/{MAX_UPLOAD_RETRIES})",
                    )
                    # Wait before retry (only if system is idle)
                    self._wait_for_retry(RETRY_DELAY_SECONDS)
                    # Re-queue for retry
                    self.upload_queue.put(video)
                else:
                    self.logger.error(
                        f"Upload failed permanently after "
                        f"{MAX_UPLOAD_RETRIES} attempts: {video.filename}",
                    )

        except Exception as e:
            self.logger.error(
                f"Upload exception: {video.filename} - {e}",
                exc_info=True,
            )
            self.storage.mark_upload_failed(video, str(e))

        finally:
            # Deactivate BLUE LED when upload completes
            self.led.set_upload_active(False)

            with self.upload_lock:
                self.currently_uploading = None

    def _wait_for_retry(self, delay_seconds: int):
        """
        Wait before retrying upload.

        Only retry when system is idle (not recording).

        Args:
            delay_seconds: How long to wait
        """
        self.logger.info(f"Waiting {delay_seconds}s before retry...")
        start_time = time.time()

        while time.time() - start_time < delay_seconds:
            if not self.running:
                return  # Shutting down

            # Wait, but check frequently if we should stop
            time.sleep(1)

        # After delay, wait until system is idle (not recording)
        while self.state == SystemState.RECORDING:
            if not self.running:
                return
            time.sleep(1)

        self.logger.info("Retry delay complete, system idle")

    # =========================================================================
    # CLEANUP OPERATIONS
    # =========================================================================

    def _start_cleanup_worker(self):
        """Start background cleanup worker thread."""
        self.logger.info("Starting cleanup worker...")
        self.cleanup_worker_thread = threading.Thread(
            target=self._cleanup_worker,
            daemon=True,
            name="CleanupWorker",
        )
        self.cleanup_worker_thread.start()

    def _cleanup_worker(self):
        """
        Background worker for automatic cleanup.

        Runs every hour:
        - Deletes uploaded videos after 7 days
        - Deletes oldest videos if more than 30 uploaded
        - Keeps disk space available
        """
        self.logger.info("Cleanup worker thread started")

        while self.running:
            try:
                # Wait until cleanup interval
                time_since_last = time.time() - self.last_cleanup_time

                if time_since_last >= CLEANUP_INTERVAL_SECONDS:
                    self.logger.info("Running automatic cleanup...")

                    # Run cleanup
                    deleted_count = self.storage.cleanup_old_videos(dry_run=False)

                    if deleted_count > 0:
                        self.logger.info(
                            f"Cleanup complete: deleted {deleted_count} videos",
                        )
                    else:
                        self.logger.debug("Cleanup complete: no videos to delete")

                    self.last_cleanup_time = time.time()

                # Sleep for 1 minute, then check again
                time.sleep(60)

            except Exception as e:
                self.logger.error(f"Cleanup worker error: {e}", exc_info=True)
                time.sleep(60)

        self.logger.info("Cleanup worker thread stopped")

    # =========================================================================
    # NETWORK MONITORING
    # =========================================================================

    def _start_network_monitor(self):
        """Start background network monitoring thread."""
        self.logger.info("Starting network monitor...")
        self.network_monitor_thread = threading.Thread(
            target=self._network_monitor_worker,
            daemon=True,
            name="NetworkMonitor",
        )
        self.network_monitor_thread.start()

    def _network_monitor_worker(self):
        """
        Background worker for network connectivity monitoring.

        Runs continuously:
        - Checks internet connectivity every NETWORK_CHECK_INTERVAL seconds
        - Updates WHITE LED status based on connectivity
        - Silent operation - just tracks and updates LED
        """
        self.logger.info("Network monitor thread started")

        while self.running:
            try:
                # Check internet connectivity
                is_connected = check_internet_connectivity()

                # Store status for metrics
                self.internet_connected = is_connected

                # Update WHITE LED status
                self.led.set_network_status(is_connected)

                # Log state changes for debugging
                if is_connected:
                    self.logger.debug("Internet: available")
                else:
                    self.logger.debug("Internet: unavailable")

                # Sleep for the configured interval
                time.sleep(NETWORK_CHECK_INTERVAL)

            except Exception as e:
                self.logger.error(f"Network monitor error: {e}", exc_info=True)
                time.sleep(NETWORK_CHECK_INTERVAL)

        self.logger.info("Network monitor thread stopped")

    # =========================================================================
    # STORAGE ERROR HANDLERS
    # =========================================================================

    def _handle_disk_full(self):
        """Handle disk full condition."""
        self.logger.error("Disk full!")
        self._transition_to_error("Disk full")

    def _handle_low_space(self):
        """Handle low disk space warning."""
        self.logger.warning("Low disk space warning")
        # Don't transition to error, just log
        # Cleanup worker will handle it

    def _handle_storage_error(self, error_message: str):
        """
        Handle storage error.

        Args:
            error_message: Description of error
        """
        self.logger.error(f"Storage error: {error_message}")
        self._transition_to_error(f"Storage error: {error_message}")

    # =========================================================================
    # ERROR RECOVERY
    # =========================================================================

    def _attempt_recovery(self):
        """
        Attempt to recover from ERROR state.

        Checks:
        1. Storage space available
        2. Camera available

        If all checks pass, transition to READY.
        """
        self.logger.info("Attempting recovery from ERROR state...")

        # Check storage
        if not self.storage.check_space():
            self.logger.error("Recovery failed: Still no disk space")
            return

        # Check camera
        if not self.camera.is_ready():
            self.logger.error("Recovery failed: Camera still not ready")
            return

        # All checks passed - recover to READY
        self.logger.info("Recovery successful!")
        self._transition_to_ready()

    # =========================================================================
    # SHUTDOWN HANDLING
    # =========================================================================

    def _signal_handler(self, signum, _frame):
        """
        Handle shutdown signals.

        Args:
            signum: Signal number
            _frame: Current stack frame (unused, required by signal API)
        """
        signal_name = signal.Signals(signum).name
        self.logger.info(f"Received signal {signal_name}, shutting down...")
        self.running = False

    def _shutdown(self):
        """
        Graceful shutdown.

        Stops recording, waits for upload to finish, cleans up hardware.
        """
        self.logger.info("Shutting down Recorder Service...")

        # Stop recording if active
        if self.current_session:
            self.logger.info("Stopping active recording session...")
            self.current_session.stop()
            self.current_session.cleanup()  # Clean up monitoring thread
            self.current_session = None

        # Wait for current upload to finish (with timeout)
        if self.currently_uploading:
            self.logger.info(
                f"Waiting for upload to complete: {self.currently_uploading.filename}",
            )
            # Wait up to 30 seconds for upload to finish
            for _ in range(30):
                if not self.currently_uploading:
                    break
                time.sleep(1)

            if self.currently_uploading:
                self.logger.warning(
                    f"Upload still running after timeout: "
                    f"{self.currently_uploading.filename}",
                )

        # Wait for worker threads to stop
        if self.upload_worker_thread and self.upload_worker_thread.is_alive():
            self.logger.info("Waiting for upload worker to stop...")
            self.upload_worker_thread.join(timeout=5.0)

        if self.cleanup_worker_thread and self.cleanup_worker_thread.is_alive():
            self.logger.info("Waiting for cleanup worker to stop...")
            self.cleanup_worker_thread.join(timeout=5.0)

        if self.network_monitor_thread and self.network_monitor_thread.is_alive():
            self.logger.info("Waiting for network monitor to stop...")
            self.network_monitor_thread.join(timeout=5.0)

        # Clean up hardware
        self.logger.info("Cleaning up hardware...")
        self.led.cleanup()
        self.button.cleanup()
        self.camera.cleanup()

        self.logger.info("Recorder Service shutdown complete")


def setup_logging():
    """
    Setup logging with rotation.

    Logs to both console and file with rotation:
    - Daily rotation
    - Keep 7 days of logs
    - Max 10MB per file
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        "%(message)s | %(name)s",
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler with rotation
    # Rotates daily, keeps 7 days
    # Define format once for both try and except blocks
    file_format = logging.Formatter(
        "%(message)s | %(name)s",
    )

    log_file = "/var/log/recorder/service.log"
    try:
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file,
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    except (PermissionError, FileNotFoundError):
        # Fallback to local logs directory if /var/log not writable
        # Create logs directory if it doesn't exist
        from pathlib import Path

        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        fallback_log = logs_dir / "recorder-service.log"
        logger.warning(
            f"Cannot write to {log_file}, using fallback: {fallback_log}",
        )
        logger.info(
            "To fix: sudo mkdir -p /var/log/recorder && "
            "sudo chown $(whoami) /var/log/recorder",
        )

        file_handler = logging.handlers.TimedRotatingFileHandler(
            str(fallback_log),
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)


def main():
    """
    Main entry point for the service.

    Sets up logging and runs the service.
    """
    # Setup logging
    setup_logging()

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Raspberry Pi Video Recorder Service Starting")
    logger.info("=" * 60)

    # Create and run service
    try:
        service = RecorderService()
        service.run()
    except Exception as e:
        logger.critical(f"Fatal error in main: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
