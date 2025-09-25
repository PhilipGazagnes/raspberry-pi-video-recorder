from enum import Enum


class SystemState(Enum):
    BOOTING = "booting"
    READY = "ready"
    RECORDING = "recording"
    PROCESSING = "processing"
    ERROR = "error"


class StateMachine:
    def __init__(self):
        self.current_state = SystemState.BOOTING
        self.state_handlers = {
            SystemState.BOOTING: self.handle_booting,
            SystemState.READY: self.handle_ready,
            SystemState.RECORDING: self.handle_recording,
            SystemState.PROCESSING: self.handle_processing,
            SystemState.ERROR: self.handle_error,
        }

    def transition_to(self, new_state):
        # Handle state transition with LED/audio updates
        pass

    def handle_button_press(self, press_type):
        # Route button press to current state handler
        pass
