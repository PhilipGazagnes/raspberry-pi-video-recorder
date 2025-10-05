import logging
import time
from enum import Enum
from typing import Callable, Dict


class SystemState(Enum):
    BOOTING = "booting"
    READY = "ready"
    RECORDING = "recording"
    PROCESSING = "processing"
    ERROR = "error"


class ButtonPress(Enum):
    SINGLE = "single"
    DOUBLE = "double"


class StateMachine:
    """
    Central state machine for the video recording system.
    Manages state transitions and coordinates component interactions.
    """

    def __init__(self):
        self.current_state = SystemState.BOOTING
        self.previous_state = None
        self.state_start_time = time.time()
        self.logger = logging.getLogger(__name__)

        # Callbacks for hardware/software components
        self.callbacks = {
            "on_state_change": None,  # Called when state changes
            "on_start_recording": None,  # Called to start recording
            "on_stop_recording": None,  # Called to stop recording
            "on_extend_recording": None,  # Called to extend recording
            "on_error": None,  # Called on error conditions
        }

        # State handlers mapping
        self.state_handlers = {
            SystemState.BOOTING: self._handle_booting,
            SystemState.READY: self._handle_ready,
            SystemState.RECORDING: self._handle_recording,
            SystemState.PROCESSING: self._handle_processing,
            SystemState.ERROR: self._handle_error,
        }

        self.logger.info("State machine initialized in BOOTING state")

    def register_callback(self, callback_name: str, callback_func: Callable):
        """Register a callback function for state machine events"""
        if callback_name in self.callbacks:
            self.callbacks[callback_name] = callback_func
            self.logger.debug(f"Registered callback: {callback_name}")
        else:
            raise ValueError(f"Unknown callback: {callback_name}")

    def get_current_state(self) -> SystemState:
        """Get the current system state"""
        return self.current_state

    def get_state_duration(self) -> float:
        """Get how long we've been in the current state (seconds)"""
        return time.time() - self.state_start_time

    def transition_to(self, new_state: SystemState, reason: str = ""):
        """
        Transition to a new state with logging and callback notification
        """
        if new_state == self.current_state:
            self.logger.debug(f"Already in state {new_state.value}")
            return

        old_state = self.current_state
        self.previous_state = old_state
        self.current_state = new_state
        self.state_start_time = time.time()

        log_msg = f"State transition: {old_state.value} -> {new_state.value}"
        if reason:
            log_msg += f" ({reason})"
        self.logger.info(log_msg)

        # Notify components of state change
        if self.callbacks["on_state_change"]:
            try:
                self.callbacks["on_state_change"](old_state, new_state)
            except Exception as e:
                self.logger.error(f"Error in state change callback: {e}")

    def handle_button_press(self, press_type: ButtonPress) -> bool:
        """
        Handle button press events based on current state
        Returns True if the button press was handled, False otherwise
        """
        self.logger.debug(
            f"Button press {press_type.value} in state {self.current_state.value}",
        )

        if self.current_state in self.state_handlers:
            return self.state_handlers[self.current_state](press_type)
        self.logger.warning(f"No handler for state {self.current_state.value}")
        return False

    def handle_system_ready(self):
        """Called when system has finished booting"""
        if self.current_state == SystemState.BOOTING:
            self.transition_to(SystemState.READY, "system initialization complete")

    def handle_recording_complete(self):
        """Called when recording has finished and needs processing"""
        if self.current_state == SystemState.RECORDING:
            self.transition_to(SystemState.PROCESSING, "recording finished")

    def handle_processing_complete(self):
        """Called when video processing/upload is complete"""
        if self.current_state == SystemState.PROCESSING:
            self.transition_to(SystemState.READY, "processing complete")

    def handle_error(self, error_msg: str = ""):
        """Called when an error occurs that requires error state"""
        self.transition_to(SystemState.ERROR, f"error occurred: {error_msg}")
        if self.callbacks["on_error"]:
            try:
                self.callbacks["on_error"](error_msg)
            except Exception as e:
                self.logger.error(f"Error in error callback: {e}")

    def handle_error_recovery(self):
        """Called when error condition has been resolved"""
        if self.current_state == SystemState.ERROR:
            self.transition_to(SystemState.READY, "error resolved")

    # State-specific button press handlers

    def _handle_booting(self, press_type: ButtonPress) -> bool:
        """Handle button presses during booting - ignore all"""
        self.logger.debug("Ignoring button press during boot")
        return False

    def _handle_ready(self, press_type: ButtonPress) -> bool:
        """Handle button presses when ready"""
        if press_type == ButtonPress.SINGLE:
            # Start recording
            self.logger.info("Starting recording session")
            self.transition_to(SystemState.RECORDING, "button press to start")

            if self.callbacks["on_start_recording"]:
                try:
                    self.callbacks["on_start_recording"]()
                except Exception as e:
                    self.logger.error(f"Error starting recording: {e}")
                    self.handle_error("failed to start recording")
                    return False
            return True

        if press_type == ButtonPress.DOUBLE:
            # Double press in ready state - could be used for system status
            self.logger.debug("Double press in ready state - no action")
            return False

        return False

    def _handle_recording(self, press_type: ButtonPress) -> bool:
        """Handle button presses during recording"""
        if press_type == ButtonPress.SINGLE:
            # Stop recording
            self.logger.info("Stopping recording session")
            self.transition_to(SystemState.PROCESSING, "button press to stop")

            if self.callbacks["on_stop_recording"]:
                try:
                    self.callbacks["on_stop_recording"]()
                except Exception as e:
                    self.logger.error(f"Error stopping recording: {e}")
                    self.handle_error("failed to stop recording")
                    return False
            return True

        if press_type == ButtonPress.DOUBLE:
            # Extend recording by 5 minutes
            self.logger.info("Extending recording session")

            if self.callbacks["on_extend_recording"]:
                try:
                    success = self.callbacks["on_extend_recording"]()
                    if not success:
                        self.logger.warning(
                            "Recording extension failed (max duration reached?)",
                        )
                        return False
                except Exception as e:
                    self.logger.error(f"Error extending recording: {e}")
                    return False
            return True

        return False

    def _handle_processing(self, press_type: ButtonPress) -> bool:
        """Handle button presses during processing - ignore all"""
        self.logger.debug("Ignoring button press during processing")
        return False

    def _handle_error(self, press_type: ButtonPress) -> bool:
        """Handle button presses in error state"""
        if press_type == ButtonPress.SINGLE:
            # Try to recover from error
            self.logger.info("Attempting error recovery")
            self.handle_error_recovery()
            return True

        if press_type == ButtonPress.DOUBLE:
            # Double press could trigger system reset or diagnostics
            self.logger.debug("Double press in error state - no action")
            return False

        return False

    def get_status_info(self) -> Dict:
        """Get detailed status information for debugging/monitoring"""
        return {
            "current_state": self.current_state.value,
            "previous_state": (
                self.previous_state.value if self.previous_state else None
            ),
            "state_duration": self.get_state_duration(),
            "callbacks_registered": {
                name: callback is not None for name, callback in self.callbacks.items()
            },
        }
