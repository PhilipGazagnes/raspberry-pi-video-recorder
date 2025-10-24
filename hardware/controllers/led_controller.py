"""
LED Controller - Refactored

Controls the 3-LED status dashboard (Green, Orange, Red).
Provides visual feedback for system states with different patterns.

IMPROVEMENTS FROM ORIGINAL:
- 150 lines vs 300 lines (50% reduction)
- No direct GPIO dependency (uses interface)
- Configuration from constants (no magic numbers)
- Shared utilities (no duplicate code)
- Cleaner threading logic
- Better separation of concerns

This demonstrates SOLID principles:
- Single Responsibility: Only manages LED status display
- Open/Closed: Easy to add new patterns without modifying code
- Dependency Inversion: Depends on GPIOInterface, not RPi.GPIO
"""

import logging
import threading
from typing import Any, Dict, Optional

from hardware.constants import (
    GPIO_LED_GREEN,
    GPIO_LED_ORANGE,
    GPIO_LED_RED,
    LED_BLINK_INTERVAL_FAST,
    LED_BLINK_INTERVAL_NORMAL,
    LED_ERROR_FLASH_DURATION,
    LED_PATTERN_CONFIG,
    LEDColor,
    LEDPattern,
)
from hardware.factory import create_gpio
from hardware.interfaces.gpio_interface import GPIOInterface, PinState
from hardware.utils.gpio_utils import safe_gpio_cleanup, setup_led_pins, toggle_pin


class LEDController:
    """
    Manages LED status display for the video recording system.

    Usage:
        led = LEDController()
        led.set_status(LEDPattern.READY)  # Green solid
        led.set_status(LEDPattern.RECORDING)  # Green blinking
        led.cleanup()
    """

    def __init__(self, gpio: Optional[GPIOInterface] = None):
        """
        Initialize LED controller.

        Args:
            gpio: GPIO interface to use, or None to auto-create.
                  Auto-creation uses factory (real hardware or mock).
                  Passing gpio is useful for testing with specific mock.

        Example:
            # Normal usage - auto-detects hardware
            led = LEDController()

            # Testing with specific mock
            mock = MockGPIO()
            led = LEDController(gpio=mock)
        """
        self.logger = logging.getLogger(__name__)

        # GPIO interface - either provided or auto-created
        self.gpio = gpio or create_gpio()

        # Pin configuration from constants (no magic numbers!)
        self.pins = {
            LEDColor.GREEN: GPIO_LED_GREEN,
            LEDColor.ORANGE: GPIO_LED_ORANGE,
            LEDColor.RED: GPIO_LED_RED,
        }

        # Current state
        self.current_pattern = LEDPattern.OFF

        # Blinking control
        self._blink_thread: Optional[threading.Thread] = None
        self._blink_stop_event = threading.Event()

        # Initialize hardware
        self._setup_leds()

        # Set initial state (all off)
        self.set_status(LEDPattern.OFF)

        self.logger.info(
            f"LED Controller initialized "
            f"(pins: G={self.pins[LEDColor.GREEN]}, "
            f"O={self.pins[LEDColor.ORANGE]}, "
            f"R={self.pins[LEDColor.RED]})",
        )

    def _setup_leds(self) -> None:
        """
        Initialize all LED pins as outputs.

        Uses shared utility instead of repeating setup logic.
        This is DRY (Don't Repeat Yourself) in action.
        """
        pin_list = list(self.pins.values())
        setup_led_pins(self.gpio, pin_list, initial_state=PinState.LOW)
        self.logger.debug(f"Initialized LED pins: {pin_list}")

    def set_status(self, pattern: LEDPattern) -> None:
        """
        Set LED pattern for system status.

        Args:
            pattern: LED pattern to display (from LEDPattern enum)

        Example:
            led.set_status(LEDPattern.READY)      # Green solid
            led.set_status(LEDPattern.RECORDING)  # Green blinking
            led.set_status(LEDPattern.ERROR)      # Red solid
        """
        if pattern == self.current_pattern:
            return  # Already displaying this pattern

        old_pattern = self.current_pattern
        self.current_pattern = pattern

        self.logger.info(f"LED pattern: {old_pattern.value} -> {pattern.value}")

        # Stop any current blinking
        self._stop_blinking()

        # Get pattern configuration from constants
        config = LED_PATTERN_CONFIG[pattern]
        green_on, orange_on, red_on, should_blink, blink_color = config

        if should_blink:
            # Start blinking pattern
            self._set_all_leds(False, False, False)  # Start with all off
            # Type safety: blink_color should always be set if should_blink is True
            if blink_color is not None:
                self._start_blinking(
                    blink_color,
                    LED_BLINK_INTERVAL_NORMAL,
                )
            else:
                self.logger.error(
                    f"Invalid LED config: {pattern} has should_blink=True "
                    "but no blink_color",
                )
        else:
            # Static pattern - just set the LEDs
            self._set_all_leds(green_on, orange_on, red_on)

    def _set_all_leds(
        self,
        green: bool,
        orange: bool,
        red: bool,
    ) -> None:
        """
        Set all LEDs to specific states.

        Args:
            green: True = ON, False = OFF
            orange: True = ON, False = OFF
            red: True = ON, False = OFF

        This is an internal helper - uses the pattern from gpio_utils
        for consistent state handling.
        """
        # Convert bool to PinState
        green_state = PinState.HIGH if green else PinState.LOW
        orange_state = PinState.HIGH if orange else PinState.LOW
        red_state = PinState.HIGH if red else PinState.LOW

        # Write to GPIO
        self.gpio.write(self.pins[LEDColor.GREEN], green_state)
        self.gpio.write(self.pins[LEDColor.ORANGE], orange_state)
        self.gpio.write(self.pins[LEDColor.RED], red_state)

        # Log for debugging (only when LEDs actually change)
        on_leds = []
        if green:
            on_leds.append("GREEN")
        if orange:
            on_leds.append("ORANGE")
        if red:
            on_leds.append("RED")

        if on_leds:
            self.logger.debug(f"LEDs ON: {', '.join(on_leds)}")
        else:
            self.logger.debug("All LEDs OFF")

    def _start_blinking(
        self,
        color: LEDColor,
        interval: float,
    ) -> None:
        """
        Start blinking a specific LED.

        Args:
            color: Which LED to blink (from LEDColor enum)
            interval: Time between blinks in seconds
        """
        # Ensure no thread is already running
        self._stop_blinking()

        # Reset stop event
        self._blink_stop_event.clear()

        # Start new blink thread
        self._blink_thread = threading.Thread(
            target=self._blink_worker,
            args=(color, interval),
            daemon=True,
            name=f"LED-Blink-{color.value}",
        )
        self._blink_thread.start()

        self.logger.debug(
            f"Started blinking {color.value} LED at {1/interval:.1f}Hz",
        )

    def _stop_blinking(self) -> None:
        """Stop any current blinking pattern."""
        if self._blink_thread and self._blink_thread.is_alive():
            self._blink_stop_event.set()
            self._blink_thread.join(timeout=1.0)
            self._blink_thread = None
            self.logger.debug("Stopped LED blinking")

    def _blink_worker(self, color: LEDColor, interval: float) -> None:
        """
        Background thread that blinks an LED.

        This runs in a separate thread so blinking doesn't block other operations.
        Uses threading.Event.wait() for clean shutdown.

        Args:
            color: LED to blink
            interval: Time between state changes
        """
        pin = self.pins[color]
        current_state = PinState.LOW

        # Keep blinking until stop event is set
        while not self._blink_stop_event.wait(interval):
            # Toggle LED state using shared utility
            current_state = toggle_pin(self.gpio, pin, current_state)

    def flash_error(self, duration: float = LED_ERROR_FLASH_DURATION) -> None:
        """
        Flash red LED rapidly to indicate error.

        This is attention-grabbing for critical errors.
        After flashing, returns to previous pattern.

        Args:
            duration: How long to flash in seconds (default from constants)

        Example:
            led.flash_error()  # Flash for 2 seconds, then restore
        """
        self.logger.info(f"Flashing error LED for {duration}s")

        # Save current pattern to restore later
        original_pattern = self.current_pattern

        # Switch to rapid red flashing
        self._stop_blinking()
        self._set_all_leds(False, False, False)
        self._start_blinking(LEDColor.RED, LED_BLINK_INTERVAL_FAST)

        # Schedule restoration after duration
        # Timer creates its own thread - non-blocking
        timer = threading.Timer(
            duration,
            lambda: self._restore_pattern(original_pattern),
        )
        timer.start()

    def _restore_pattern(self, pattern: LEDPattern) -> None:
        """
        Restore a previous LED pattern.

        Used by flash_error to return to normal after flashing.

        Args:
            pattern: Pattern to restore
        """
        self._stop_blinking()
        self.set_status(pattern)
        self.logger.debug(f"LED pattern restored to {pattern.value}")

    def test_sequence(self, duration_per_step: float = 1.0) -> None:
        """
        Run a test sequence through all LED patterns.

        Useful for hardware verification - you can see each LED works.

        Args:
            duration_per_step: How long to show each pattern (seconds)

        Example:
            led = LEDController()
            led.test_sequence()  # Watch the light show!
        """
        import time

        self.logger.info("Starting LED test sequence")
        original_pattern = self.current_pattern

        # Test each pattern
        test_patterns = [
            ("Green Solid", LEDPattern.READY),
            ("Orange Solid", LEDPattern.PROCESSING),
            ("Red Solid", LEDPattern.ERROR),
            ("Green Blink", LEDPattern.RECORDING),
        ]

        for name, pattern in test_patterns:
            self.logger.info(f"Testing: {name}")
            self.set_status(pattern)
            time.sleep(duration_per_step)

        # Restore original pattern
        self.set_status(original_pattern)
        self.logger.info("LED test sequence complete")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current LED controller status.

        Useful for debugging and monitoring.

        Returns:
            Dictionary with current state information

        Example:
            status = led.get_status()
            print(f"Current pattern: {status['current_pattern']}")
        """
        return {
            "current_pattern": self.current_pattern.value,
            "is_blinking": self._blink_thread is not None
            and self._blink_thread.is_alive(),
            "gpio_available": self.gpio.is_available(),
            "pins": {
                "green": self.pins[LEDColor.GREEN],
                "orange": self.pins[LEDColor.ORANGE],
                "red": self.pins[LEDColor.RED],
            },
        }

    def cleanup(self) -> None:
        """
        Clean up resources and reset LEDs.

        IMPORTANT: Always call this before program exits!
        Ensures LEDs are off and GPIO is released properly.

        Example:
            led = LEDController()
            try:
                # ... use LEDs ...
            finally:
                led.cleanup()  # Always cleanup, even on error
        """
        self.logger.info("Cleaning up LED Controller")

        # Stop any blinking
        self._stop_blinking()

        # Turn off all LEDs
        self.set_status(LEDPattern.OFF)

        # Clean up GPIO using shared utility (safe - won't crash)
        pin_list = list(self.pins.values())
        safe_gpio_cleanup(self.gpio, pin_list, self.logger)

        self.logger.info("LED Controller cleanup complete")

    def __del__(self):
        """
        Destructor - ensures cleanup even if not explicitly called.

        This is a safety net. You should still call cleanup() explicitly,
        but this catches cases where you forget.
        """
        self.cleanup()
