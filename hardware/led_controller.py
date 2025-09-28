import logging
import threading
import time
from enum import Enum
from typing import Optional

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO not available - LED controller will run in simulation mode")


class LEDStatus(Enum):
    """LED status patterns for the video recording system"""
    OFF = "off"                    # All LEDs off (system booting)
    READY = "ready"               # Green solid (ready to record)
    RECORDING = "recording"        # Green blinking (recording in progress)
    PROCESSING = "processing"      # Orange solid (processing/uploading)
    ERROR = "error"               # Red solid (error state)


class LEDController:
    """
    Controls the 3-LED status dashboard for the video recording system.
    Provides visual feedback for system states with different patterns.
    """

    def __init__(self, green_pin: int, orange_pin: int, red_pin: int):
        self.green_pin = green_pin
        self.orange_pin = orange_pin
        self.red_pin = red_pin

        self.current_status = LEDStatus.OFF
        self.logger = logging.getLogger(__name__)

        # Blinking control
        self._blinking = False
        self._blink_thread = None
        self._blink_stop_event = threading.Event()

        # Initialize GPIO
        if GPIO_AVAILABLE:
            self._setup_gpio()
        else:
            self.logger.warning("Running in simulation mode - no actual GPIO control")

        # Set initial state
        self.set_status(LEDStatus.OFF)
        self.logger.info(f"LED Controller initialized (pins: G={green_pin}, O={orange_pin}, R={red_pin})")

    def _setup_gpio(self):
        """Initialize GPIO pins for LED control"""
        try:
            # Set GPIO mode
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # Setup output pins
            GPIO.setup(self.green_pin, GPIO.OUT)
            GPIO.setup(self.orange_pin, GPIO.OUT)
            GPIO.setup(self.red_pin, GPIO.OUT)

            # Start with all LEDs off
            GPIO.output(self.green_pin, GPIO.LOW)
            GPIO.output(self.orange_pin, GPIO.LOW)
            GPIO.output(self.red_pin, GPIO.LOW)

            self.logger.info("GPIO pins initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize GPIO: {e}")
            raise

    def set_status(self, status: LEDStatus):
        """
        Set LED status with appropriate pattern
        """
        if status == self.current_status:
            return  # No change needed

        old_status = self.current_status
        self.current_status = status

        self.logger.info(f"LED status change: {old_status.value} -> {status.value}")

        # Stop any current blinking
        self.stop_blinking()

        # Apply the new status pattern
        if status == LEDStatus.OFF:
            self._set_all_leds(False, False, False)

        elif status == LEDStatus.READY:
            self._set_all_leds(True, False, False)  # Green solid

        elif status == LEDStatus.RECORDING:
            self._set_all_leds(False, False, False)  # Start with all off
            self.start_blinking("green", 0.5)  # Green blinking at 1Hz

        elif status == LEDStatus.PROCESSING:
            self._set_all_leds(False, True, False)  # Orange solid

        elif status == LEDStatus.ERROR:
            self._set_all_leds(False, False, True)  # Red solid

        else:
            self.logger.warning(f"Unknown LED status: {status}")

    def _set_all_leds(self, green: bool, orange: bool, red: bool):
        """Set all LEDs to specific states"""
        if GPIO_AVAILABLE:
            GPIO.output(self.green_pin, GPIO.HIGH if green else GPIO.LOW)
            GPIO.output(self.orange_pin, GPIO.HIGH if orange else GPIO.LOW)
            GPIO.output(self.red_pin, GPIO.HIGH if red else GPIO.LOW)

        # Log the change for debugging/simulation
        states = []
        if green: states.append("GREEN")
        if orange: states.append("ORANGE")
        if red: states.append("RED")

        if states:
            self.logger.debug(f"LEDs ON: {', '.join(states)}")
        else:
            self.logger.debug("All LEDs OFF")

    def start_blinking(self, color: str, interval: float = 0.5):
        """
        Start blinking a specific LED color

        Args:
            color: "green", "orange", or "red"
            interval: Blink interval in seconds (default 0.5s = 1Hz)
        """
        if self._blinking:
            self.stop_blinking()

        self._blinking = True
        self._blink_stop_event.clear()

        # Start blink thread
        self._blink_thread = threading.Thread(
            target=self._blink_worker,
            args=(color, interval),
            daemon=True
        )
        self._blink_thread.start()

        self.logger.debug(f"Started blinking {color} LED at {1/interval}Hz")

    def stop_blinking(self):
        """Stop any current blinking pattern"""
        if self._blinking:
            self._blinking = False
            self._blink_stop_event.set()

            if self._blink_thread and self._blink_thread.is_alive():
                self._blink_thread.join(timeout=1.0)

            self.logger.debug("Stopped LED blinking")

    def _blink_worker(self, color: str, interval: float):
        """Worker thread for blinking LEDs"""
        pin_map = {
            "green": self.green_pin,
            "orange": self.orange_pin,
            "red": self.red_pin
        }

        if color not in pin_map:
            self.logger.error(f"Invalid blink color: {color}")
            return

        pin = pin_map[color]
        led_state = False

        while self._blinking and not self._blink_stop_event.wait(interval):
            led_state = not led_state

            if GPIO_AVAILABLE:
                GPIO.output(pin, GPIO.HIGH if led_state else GPIO.LOW)

            # Debug logging (less frequent to avoid spam)
            if led_state:  # Only log on LED turn-on
                self.logger.debug(f"{color.upper()} LED blink")

    def flash_error(self, duration: float = 2.0):
        """
        Flash red LED rapidly for error indication

        Args:
            duration: How long to flash in seconds
        """
        self.logger.info(f"Flashing error LED for {duration}s")

        # Save current status
        original_status = self.current_status

        # Flash red rapidly
        self.set_status(LEDStatus.OFF)
        self.start_blinking("red", 0.1)  # 5Hz rapid flash

        # Stop after duration and restore
        threading.Timer(duration, self._restore_status, args=(original_status,)).start()

    def _restore_status(self, original_status: LEDStatus):
        """Restore LED status after flash"""
        self.stop_blinking()
        self.set_status(original_status)
        self.logger.debug("LED status restored after flash")

    def test_sequence(self, duration_per_led: float = 1.0):
        """
        Run a test sequence of all LEDs for hardware verification

        Args:
            duration_per_led: How long to show each LED in seconds
        """
        self.logger.info("Starting LED test sequence")
        original_status = self.current_status

        # Test each LED individually
        test_sequence = [
            ("Green", LEDStatus.READY),
            ("Orange", LEDStatus.PROCESSING),
            ("Red", LEDStatus.ERROR),
            ("Green Blink", LEDStatus.RECORDING)
        ]

        for name, status in test_sequence:
            self.logger.info(f"Testing {name}")
            self.set_status(status)
            time.sleep(duration_per_led)

        # Restore original status
        self.set_status(original_status)
        self.logger.info("LED test sequence complete")

    def get_status(self) -> dict:
        """Get current LED status information"""
        return {
            'current_status': self.current_status.value,
            'is_blinking': self._blinking,
            'gpio_available': GPIO_AVAILABLE,
            'pins': {
                'green': self.green_pin,
                'orange': self.orange_pin,
                'red': self.red_pin
            }
        }

    def cleanup(self):
        """Clean up GPIO resources"""
        self.logger.info("Cleaning up LED Controller")

        # Stop blinking
        self.stop_blinking()

        # Turn off all LEDs
        self.set_status(LEDStatus.OFF)

        # Cleanup GPIO
        if GPIO_AVAILABLE:
            try:
                GPIO.cleanup([self.green_pin, self.orange_pin, self.red_pin])
                self.logger.info("GPIO cleanup complete")
            except Exception as e:
                self.logger.error(f"Error during GPIO cleanup: {e}")

    def __del__(self):
        """Destructor - ensure cleanup"""
        self.cleanup()
