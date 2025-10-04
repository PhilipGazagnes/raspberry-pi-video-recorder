# Role: Central coordinator and state manager
#
# Manages the main state machine (READY → RECORDING → PROCESSING → READY)
# Coordinates all other components
# Handles systemd service lifecycle
# Implements graceful shutdown

import time

from core.state_machine import StateMachine
from hardware.controllers.audio_controller import AudioController
from hardware.controllers.button_controller import ButtonController
from hardware.controllers.led_controller import LEDController
from recording.camera_manager import CameraManager
from storage.storage_manager import StorageManager
from upload.upload_manager import UploadManager


class BoxingRecorderService:
    def __init__(self):
        # Initialize all components
        self.running = True
        self.state_machine = StateMachine()
        self.button_controller = ButtonController(gpio_pin=18)
        self.led_controller = LEDController(green=12, orange=16, red=20)
        self.audio_controller = AudioController()
        self.camera_manager = CameraManager()
        self.upload_manager = UploadManager()
        self.storage_manager = StorageManager()
        self.current_session = None

    def run(self):
        # Main service loop
        while self.running:
            self.process_button_events()
            self.check_recording_status()
            self.update_system_status()
            self.handle_warnings()
            time.sleep(0.1)  # 10Hz update rate

    def process_button_events(self):
        # Handle button press events based on current state
        pass

    def check_recording_status(self):
        # Monitor active recording sessions
        # Handle auto-stop and warnings
        pass

    def handle_warnings(self):
        # Check for 1-minute warning
        # Handle storage space warnings
        pass
