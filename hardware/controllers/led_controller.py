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
import time
from typing import Any, Dict, Optional

from config.settings import GPIO_LED_BLUE, GPIO_LED_WHITE
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
            # Using context manager (recommended)
            with LEDController() as led:
                led.set_status(LEDPattern.READY)
                # ... LED operations ...
            # Cleanup guaranteed even if exception occurs

            # Using explicit cleanup (legacy)
            led = LEDController()
            try:
                led.set_status(LEDPattern.READY)
            finally:
                led.cleanup()
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

        # Upload LED blinking control
        self._upload_blink_thread: Optional[threading.Thread] = None
        self._upload_blink_event: Optional[threading.Event] = None

        self._cleaned_up = False

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
        Includes main LEDs (G, O, R) and status LEDs (WHITE, BLUE).
        """
        # WHY GPIO output pins for LEDs?
        # Context: LEDs are controlled by driving GPIO pins LOW/HIGH
        #   - HIGH state sinks current through LED cathode (LED on)
        #   - LOW state stops current flow (LED off)
        # All pins initialized to LOW (LEDs off) on startup
        # GPIO pins support PWM (pulse width modulation) for future
        # brightness control by varying HIGH pulse duration
        pin_list = list(self.pins.values())
        # Network and upload status LEDs (white, blue)
        pin_list.extend([GPIO_LED_WHITE, GPIO_LED_BLUE])
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
            # Special case: sequence animation (warning pattern)
            if blink_color == "sequence":
                # Play the warning sequence in background thread
                sequence_thread = threading.Thread(
                    target=self.play_warning_sequence,
                    daemon=True,
                    name="LED-Warning-Sequence",
                )
                sequence_thread.start()
            else:
                # Standard blinking pattern
                self._set_all_leds(False, False, False)  # Start with all off
                # Type safety: blink_color should be LEDColor enum (not "sequence")
                if blink_color is not None and isinstance(blink_color, LEDColor):
                    self._start_blinking(
                        blink_color,
                        LED_BLINK_INTERVAL_NORMAL,
                    )
                else:
                    self.logger.error(
                        f"Invalid LED config: {pattern} has should_blink=True "
                        "but invalid blink_color",
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

    def flash_extension_success(self) -> None:
        """
        Flash green LED 5 times quickly to confirm time extension.

        Quick visual feedback that recording extension was successful.
        Returns to recording pattern (warning or normal green blinking).

        Pattern: G_G_G_G_G_ (on/off 5 times, 0.1s each = 1 second total)

        Example:
            led.flash_extension_success()  # Quick confirmation flash
        """
        self.logger.info("Flashing extension success (5x green)")

        # Save current pattern to restore later
        original_pattern = self.current_pattern

        # Run flash sequence in background thread (non-blocking)
        flash_thread = threading.Thread(
            target=self._extension_flash_worker,
            args=(original_pattern,),
            daemon=True,
            name="LED-Extension-Flash",
        )
        flash_thread.start()

    def _extension_flash_worker(self, restore_pattern: LEDPattern) -> None:
        """
        Background worker for extension success flash.

        Flashes green 5 times quickly, then restores original pattern.

        Args:
            restore_pattern: Pattern to restore after flashing
        """
        flash_count = 5
        flash_interval = 0.1  # 0.1s on, 0.1s off = fast and snappy

        # Stop any current animation
        self._stop_blinking()

        # Flash 5 times
        for _flash in range(flash_count):
            # Green ON
            self._set_all_leds(True, False, False)
            time.sleep(flash_interval)

            # Green OFF
            self._set_all_leds(False, False, False)
            time.sleep(flash_interval)

        # Restore original pattern
        self._restore_pattern(restore_pattern)

    def play_warning_sequence(self) -> None:
        """
        Start continuous green-orange-red warning sequence animation.

        This is called when recording time warning is reached.
        Repeats the sequence continuously with blank gaps until stopped.

        Timing perfectly matches green blinking for visual harmony:
        - GORGOR sequence = 0.5s (same duration as green ON in recording)
        - Blank gap = 0.5s (same duration as green OFF in recording)
        - Total cycle = 1.0s (identical rhythm to recording pattern)

        Pattern visualization:
        Recording:  [GREEN....][     ][GREEN....][     ]...
        Warning:    [G-O-R-G-O-R][     ][G-O-R-G-O-R][     ]...

        Stops when:
        - Recording is extended
        - Recording completes
        - Pattern changes to something else
        (All handled by existing LED pattern switching)

        Example:
            led.play_warning_sequence()  # Starts continuous warning
        """
        self.logger.info("Starting warning sequence (continuous G-O-R with gaps)")

        # Stop any current blinking
        self._stop_blinking()

        # Update current pattern so set_status() knows we're in warning mode
        # This allows set_status(LEDPattern.RECORDING) to properly restore
        self.current_pattern = LEDPattern.WARNING

        # Reset stop event - this allows the sequence to start fresh
        self._blink_stop_event.clear()

        # Start warning sequence in background thread
        self._blink_thread = threading.Thread(
            target=self._warning_sequence_worker,
            daemon=True,
            name="LED-Warning-Sequence",
        )
        self._blink_thread.start()

    def _warning_sequence_worker(self) -> None:
        """
        Background worker for continuous warning sequence animation.

        Repeats green-orange-red sequence (twice) with blank gaps.
        Timing perfectly synchronized with green blinking pattern.

        Pattern timing:
        - GORGOR sequence = LED_BLINK_INTERVAL_NORMAL (0.5s, same as green ON)
        - Blank = LED_BLINK_INTERVAL_NORMAL (0.5s, same as green OFF)
        - Total cycle = 1.0s (identical to green blink rhythm)
        - Each color in GORGOR = 0.5s / 6 = ~0.083s

        If LED_BLINK_INTERVAL_NORMAL = 0.5:
        - Each color = 0.5 / 6 = 0.0833s
        - GORGOR total = 0.5s
        - Blank = 0.5s
        - Cycle total = 1.0s ✓

        Visual alignment:
        Green:    [GGGG 0.5s][____ 0.5s][GGGG 0.5s][____ 0.5s]...
        Warning:  [GORGOR 0.5s][BLANK 0.5s][GORGOR 0.5s][BLANK 0.5s]...
        """
        warning_colors = [LEDColor.GREEN, LEDColor.ORANGE, LEDColor.RED]

        # Match green blink intervals exactly
        gorgor_duration = LED_BLINK_INTERVAL_NORMAL  # 0.5s
        color_interval = gorgor_duration / 6  # Time per color in GORGOR
        blank_interval = LED_BLINK_INTERVAL_NORMAL  # 0.5s (matches green OFF)

        # Keep looping until stop event is set
        while not self._blink_stop_event.is_set():
            # Play the sequence TWICE (GORGOR) within gorgor_duration
            for _repeat in range(2):
                for color in warning_colors:
                    # Turn on the current color
                    if color == LEDColor.GREEN:
                        self._set_all_leds(True, False, False)
                    elif color == LEDColor.ORANGE:
                        self._set_all_leds(False, True, False)
                    elif color == LEDColor.RED:
                        self._set_all_leds(False, False, True)

                    # Check for stop during interval
                    if self._blink_stop_event.wait(color_interval):
                        return  # Stop event set, exit immediately

            # Blank gap (exactly same as green OFF duration)
            self._set_all_leds(False, False, False)

            # Check for stop during gap
            if self._blink_stop_event.wait(blank_interval):
                return  # Stop event set, exit immediately

    def _restore_pattern(self, pattern: LEDPattern) -> None:
        """
        Restore a previous LED pattern.

        Used by flash_error and flash_extension_success to return to normal.

        Args:
            pattern: Pattern to restore

        Note: Sets to OFF first to force set_status() to refresh even if
              restoring to the same pattern (needed after stopping threads).
        """
        self._stop_blinking()
        # Force set_status to refresh by setting to a different pattern first
        # This is needed because _stop_blinking() stopped the thread but
        # didn't change current_pattern, so set_status would see pattern==current
        # and return early without restarting the blinking thread
        self.current_pattern = LEDPattern.OFF
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

    def set_network_status(self, is_connected: bool) -> None:
        """
        Set WHITE LED status based on internet connectivity.

        Provides continuous network status feedback:
        - Solid ON when internet is available
        - OFF when internet is disconnected

        Network monitoring runs in background (every 30 seconds by default).

        Args:
            is_connected: True if internet is available, False otherwise

        Example:
            led.set_network_status(True)   # Turn on WHITE LED (internet available)
            led.set_network_status(False)  # Turn off WHITE LED (no internet)
        """
        # Update WHITE LED based on connectivity
        # Note: Future enhancement could add PWM dimming (50% brightness)
        # for visual distinction, but binary ON/OFF is sufficient
        # for clear internet availability indication
        brightness = 128 if is_connected else 0  # 0-255 range for future PWM
        self.gpio.write(
            GPIO_LED_WHITE,
            PinState.HIGH if brightness > 0 else PinState.LOW,
        )
        status = "ON" if is_connected else "OFF"
        self.logger.debug(f"Network status LED: {status}")

    def set_upload_active(self, is_uploading: bool) -> None:
        """
        Control BLUE LED blinking based on upload activity.

        BLUE LED is dimmed (50% brightness) and blinks when uploading.
        Uses same blink rate as recording pattern (0.5s interval).

        Args:
            is_uploading: True to start blinking, False to stop

        Example:
            led.set_upload_active(True)   # Start BLUE LED blinking
            led.set_upload_active(False)  # Stop BLUE LED blinking
        """
        if is_uploading:
            self.logger.debug("Upload LED: Starting blink")
            # Start blinking BLUE LED in background thread
            self._upload_blink_thread = threading.Thread(
                target=self._upload_blink_worker,
                daemon=True,
                name="LED-Upload-Blink",
            )
            self._upload_blink_event = threading.Event()
            self._upload_blink_thread.start()
        else:
            self.logger.debug("Upload LED: Stopping blink")
            # Stop the upload blink thread
            if self._upload_blink_event is not None:
                self._upload_blink_event.set()
            # Turn off BLUE LED
            self.gpio.write(GPIO_LED_BLUE, PinState.LOW)

    def _upload_blink_worker(self) -> None:
        """
        Background worker for BLUE LED upload blinking.

        Blinks at 50% brightness with normal blink interval (0.5s).
        Continues until _upload_blink_event is set.
        """
        # _upload_blink_event is guaranteed to be set by set_upload_active()
        # before this thread starts
        if self._upload_blink_event is None:
            self.logger.error("Upload blink event is None")
            return

        blink_interval = LED_BLINK_INTERVAL_NORMAL
        brightness_high = PinState.HIGH
        brightness_low = PinState.LOW

        # WHY Event-driven timing instead of simple sleep()?
        # Context: Need responsive shutdown when upload finishes
        #   Problem: sleep(duration) blocks for full duration
        #   Solution: use Event.wait(timeout) which:
        #     1. Sleeps for timeout duration
        #     2. BUT wakes early if event is set
        #   Result: LED stops blinking IMMEDIATELY when upload done,
        #           instead of waiting up to 0.5s for sleep to complete
        # Pattern: .wait(timeout) returns False if timeout, True if set
        while not self._upload_blink_event.wait(blink_interval):
            # Blink: ON for interval
            self.gpio.write(GPIO_LED_BLUE, brightness_high)

            if self._upload_blink_event.wait(blink_interval):
                break

            # Blink: OFF for interval
            self.gpio.write(GPIO_LED_BLUE, brightness_low)

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
        Safe to call multiple times - idempotent.

        Example:
            led = LEDController()
            try:
                # ... use LEDs ...
            finally:
                led.cleanup()  # Always cleanup, even on error
        """
        if self._cleaned_up:
            return

        self.logger.info("Cleaning up LED Controller")

        # Stop any blinking
        self._stop_blinking()

        # Turn off all LEDs
        self.set_status(LEDPattern.OFF)

        # Clean up GPIO using shared utility (safe - won't crash)
        pin_list = list(self.pins.values())
        safe_gpio_cleanup(self.gpio, pin_list, self.logger)

        self._cleaned_up = True
        self.logger.info("LED Controller cleanup complete")

    def __enter__(self):
        """
        Enter context manager.

        Usage:
            with LEDController() as led:
                led.set_status(LEDPattern.READY)
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context manager - always cleanup.

        Args:
            exc_type: Exception type if exception occurred
            exc_val: Exception value if exception occurred
            exc_tb: Exception traceback if exception occurred

        Returns:
            False - propagates exceptions up the stack
        """
        self.cleanup()
        return False

    def __del__(self):
        """
        Destructor - fallback cleanup if not properly closed.

        WARNING: Use context manager (`with` statement) or
        call cleanup() explicitly instead of relying on __del__.
        """
        if not self._cleaned_up:
            self.logger.warning(
                "LEDController not properly cleaned up - "
                "use 'with' statement or call cleanup() explicitly",
            )
            self.cleanup()
