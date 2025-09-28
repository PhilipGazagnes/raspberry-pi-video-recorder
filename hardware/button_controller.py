import logging
import threading
import time
from typing import Callable, Optional

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO not available - Button controller will run in simulation mode")


class ButtonPress:
    """Represents different types of button press events"""
    SINGLE = "single"
    DOUBLE = "double"


class ButtonController:
    """
    Handles button input for the video recording system with debouncing
    and single/double-tap detection.
    """

    def __init__(self, gpio_pin: int, pull_up: bool = True):
        self.gpio_pin = gpio_pin
        self.pull_up = pull_up
        self.logger = logging.getLogger(__name__)

        # Button timing configuration
        self.debounce_time = 0.05  # 50ms debounce
        self.double_tap_window = 0.5  # 500ms window for double tap

        # State tracking
        self.last_press_time = 0
        self.pending_single_press = False
        self.callback_func: Optional[Callable] = None

        # Threading for non-blocking operation
        self._button_thread = None
        self._running = False
        self._single_press_timer = None

        # Initialize GPIO
        if GPIO_AVAILABLE:
            self._setup_gpio()
        else:
            self.logger.warning("Running in simulation mode - no actual GPIO control")
            # Start simulation mode for development/testing
            self._start_simulation_mode()

        self.logger.info(f"Button Controller initialized (pin: {gpio_pin}, pull_up: {pull_up})")

    def _setup_gpio(self):
        """Initialize GPIO pin for button input"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # Setup input pin with pull-up or pull-down resistor
            if self.pull_up:
                GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            else:
                GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

            # Setup interrupt for falling edge (button press with pull-up)
            # or rising edge (button press with pull-down)
            edge = GPIO.FALLING if self.pull_up else GPIO.RISING
            GPIO.add_event_detect(
                self.gpio_pin,
                edge,
                callback=self._gpio_callback,
                bouncetime=int(self.debounce_time * 1000)  # Convert to milliseconds
            )

            self.logger.info("GPIO button setup complete")

        except Exception as e:
            self.logger.error(f"Failed to initialize GPIO for button: {e}")
            raise

    def _start_simulation_mode(self):
        """Start simulation mode for development without GPIO"""
        self.logger.info("Starting button simulation mode")
        self.logger.info("Press 's' + Enter for single press, 'd' + Enter for double press, 'q' to quit")

        self._running = True
        self._button_thread = threading.Thread(target=self._simulation_worker, daemon=True)
        self._button_thread.start()

    def _simulation_worker(self):
        """Worker thread for simulation mode input"""
        try:
            while self._running:
                try:
                    user_input = input().strip().lower()

                    if user_input == 'q':
                        self.logger.info("Simulation mode quit requested")
                        break
                    elif user_input == 's':
                        self.logger.info("Simulating single button press")
                        self._handle_button_event()
                    elif user_input == 'd':
                        self.logger.info("Simulating double button press")
                        self._handle_button_event()
                        time.sleep(0.1)  # Small delay between presses
                        self._handle_button_event()

                except (EOFError, KeyboardInterrupt):
                    break

        except Exception as e:
            self.logger.error(f"Error in simulation worker: {e}")

    def _gpio_callback(self, channel):
        """GPIO interrupt callback for button press detection"""
        current_time = time.time()

        # Simple debouncing - ignore if too soon after last press
        if current_time - self.last_press_time < self.debounce_time:
            return

        self.last_press_time = current_time
        self._handle_button_event()

    def _handle_button_event(self):
        """Process a button press event and determine single vs double tap"""
        current_time = time.time()

        if self.pending_single_press:
            # This is a second press within the double-tap window
            if current_time - self.last_press_time <= self.double_tap_window:
                self.logger.debug("Double tap detected")
                self._cancel_single_press_timer()
                self.pending_single_press = False
                self._trigger_callback(ButtonPress.DOUBLE)
                return

        # This is potentially a single press
        self.pending_single_press = True
        self.last_press_time = current_time

        # Start timer to trigger single press if no second press comes
        self._single_press_timer = threading.Timer(
            self.double_tap_window,
            self._trigger_single_press
        )
        self._single_press_timer.start()

        self.logger.debug("Button press registered, waiting for potential double tap")

    def _trigger_single_press(self):
        """Trigger single press callback after double-tap window expires"""
        if self.pending_single_press:
            self.logger.debug("Single tap confirmed")
            self.pending_single_press = False
            self._trigger_callback(ButtonPress.SINGLE)

    def _cancel_single_press_timer(self):
        """Cancel pending single press timer"""
        if self._single_press_timer:
            self._single_press_timer.cancel()
            self._single_press_timer = None

    def _trigger_callback(self, press_type: str):
        """Trigger the registered callback with the press type"""
        if self.callback_func:
            try:
                self.logger.info(f"Button {press_type} press - triggering callback")
                self.callback_func(press_type)
            except Exception as e:
                self.logger.error(f"Error in button callback: {e}")
        else:
            self.logger.warning(f"Button {press_type} press detected but no callback registered")

    def register_callback(self, callback_func: Callable[[str], None]):
        """
        Register a callback function to be called on button press

        Args:
            callback_func: Function that takes press_type (string) as argument
        """
        self.callback_func = callback_func
        self.logger.info("Button callback registered")

    def set_timing(self, debounce_time: float = None, double_tap_window: float = None):
        """
        Adjust button timing parameters

        Args:
            debounce_time: Debounce time in seconds (default: 0.05)
            double_tap_window: Double tap detection window in seconds (default: 0.5)
        """
        if debounce_time is not None:
            self.debounce_time = debounce_time
            self.logger.info(f"Debounce time set to {debounce_time}s")

        if double_tap_window is not None:
            self.double_tap_window = double_tap_window
            self.logger.info(f"Double tap window set to {double_tap_window}s")

    def test_button(self):
        """Test button functionality - useful for hardware verification"""
        self.logger.info("Starting button test - press button to verify functionality")

        def test_callback(press_type):
            self.logger.info(f"✓ Button test: {press_type} press detected successfully")

        # Temporarily register test callback
        original_callback = self.callback_func
        self.register_callback(test_callback)

        # In simulation mode, provide instructions
        if not GPIO_AVAILABLE:
            self.logger.info("Test mode: Press 's' for single, 'd' for double, any other key to end test")
            try:
                input("Press Enter to end test...")
            except KeyboardInterrupt:
                pass
        else:
            self.logger.info("Press the button to test (Ctrl+C to end test)")
            try:
                time.sleep(10)  # Test for 10 seconds
            except KeyboardInterrupt:
                pass

        # Restore original callback
        self.callback_func = original_callback
        self.logger.info("Button test complete")

    def get_status(self) -> dict:
        """Get current button controller status"""
        return {
            'gpio_pin': self.gpio_pin,
            'pull_up': self.pull_up,
            'gpio_available': GPIO_AVAILABLE,
            'debounce_time': self.debounce_time,
            'double_tap_window': self.double_tap_window,
            'pending_single_press': self.pending_single_press,
            'callback_registered': self.callback_func is not None,
            'last_press_time': self.last_press_time
        }

    def cleanup(self):
        """Clean up GPIO resources and stop threads"""
        self.logger.info("Cleaning up Button Controller")

        # Stop simulation mode
        self._running = False

        # Cancel any pending timers
        self._cancel_single_press_timer()

        # Cleanup GPIO
        if GPIO_AVAILABLE:
            try:
                GPIO.remove_event_detect(self.gpio_pin)
                GPIO.cleanup(self.gpio_pin)
                self.logger.info("GPIO cleanup complete")
            except Exception as e:
                self.logger.error(f"Error during GPIO cleanup: {e}")

    def __del__(self):
        """Destructor - ensure cleanup"""
        self.cleanup()
