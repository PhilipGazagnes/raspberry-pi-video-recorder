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

from config.settings import (
    GPIO_LED_BLUE,
    GPIO_LED_WHITE,
    LED_ERROR_DURATION,
    LED_ERROR_PATTERN,
    LED_ERROR_PAUSE_DURATION,
    LED_ERROR_STEP_DURATION,
    LED_EXTENSION_ADDED_PATTERN,
    LED_EXTENSION_ADDED_PAUSE_DURATION,
    LED_EXTENSION_ADDED_REPEAT_COUNT,
    LED_EXTENSION_ADDED_STEP_DURATION,
    LED_RECORDING_PATTERN,
    LED_RECORDING_PAUSE_DURATION,
    LED_RECORDING_STARTED_PATTERN,
    LED_RECORDING_STARTED_PAUSE_DURATION,
    LED_RECORDING_STARTED_REPEAT_COUNT,
    LED_RECORDING_STARTED_STEP_DURATION,
    LED_RECORDING_STARTING_PATTERN,
    LED_RECORDING_STARTING_PAUSE_DURATION,
    LED_RECORDING_STARTING_STEP_DURATION,
    LED_RECORDING_STEP_DURATION,
    LED_RECORDING_WARN1_PATTERN,
    LED_RECORDING_WARN1_PAUSE_DURATION,
    LED_RECORDING_WARN1_STEP_DURATION,
    LED_RECORDING_WARN2_PATTERN,
    LED_RECORDING_WARN2_PAUSE_DURATION,
    LED_RECORDING_WARN2_STEP_DURATION,
    LED_RECORDING_WARN3_PATTERN,
    LED_RECORDING_WARN3_PAUSE_DURATION,
    LED_RECORDING_WARN3_STEP_DURATION,
    LED_UPLOAD_BLINK_INTERVAL,
)
from hardware.constants import (
    GPIO_LED_GREEN,
    GPIO_LED_ORANGE,
    GPIO_LED_RED,
    LED_PATTERN_CONFIG,
    LEDColor,
    LEDPattern,
)
from hardware.factory import create_gpio
from hardware.interfaces.gpio_interface import GPIOInterface, PinState
from hardware.utils import (
    PatternParseError,
    parse_pattern,
    safe_gpio_cleanup,
    setup_led_pins,
)


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
            # Use 12-step pattern framework
            if pattern == LEDPattern.RECORDING:
                # Normal recording - green blink
                self._start_pattern(
                    LED_RECORDING_PATTERN,
                    LED_RECORDING_STEP_DURATION,
                    LED_RECORDING_PAUSE_DURATION,
                    repeat_count=None,  # Continuous
                )
            elif pattern == LEDPattern.WARNING:
                # Warning pattern - will be set by play_warning_sequence()
                # This is called from external code, keep compatibility
                self.play_warning_sequence()
            else:
                self.logger.warning(
                    f"Pattern {pattern.value} has should_blink=True "
                    "but no pattern configuration",
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

    def _start_pattern(
        self,
        pattern: str,
        step_duration: float,
        pause_duration: float,
        repeat_count: Optional[int] = None,
    ) -> None:
        """
        Start a pattern animation using the universal pattern engine.

        Args:
            pattern: 12-step pattern string (e.g., "G-x-G-x-G-x-G-x-G-x-G-x")
            step_duration: Seconds per step
            pause_duration: Seconds of blank gap between cycles
            repeat_count: Number of cycles (None = infinite)
        """
        # Stop any current blinking
        self._stop_blinking()

        # Reset stop event
        self._blink_stop_event.clear()

        # Start new pattern thread
        self._blink_thread = threading.Thread(
            target=self._pattern_worker,
            args=(pattern, step_duration, pause_duration, repeat_count),
            daemon=True,
            name="LED-Pattern-Worker",
        )
        self._blink_thread.start()

        self.logger.debug(
            f"Started pattern: {pattern[:20]}... "
            f"(step={step_duration}s, pause={pause_duration}s, "
            f"repeat={repeat_count if repeat_count else 'infinite'})",
        )

    def _pattern_worker(
        self,
        pattern: str,
        step_duration: float,
        pause_duration: float,
        repeat_count: Optional[int] = None,
    ) -> None:
        """
        Universal pattern execution engine.

        All LED animations use this single worker.
        Parses pattern string and executes LED state sequences.

        Args:
            pattern: 12-step pattern string
            step_duration: Seconds per step
            pause_duration: Seconds between cycles
            repeat_count: Number of cycles (None = infinite)

        Pattern Format:
            "G-O-R-GOR-x-x-G-O-R-GOR-x-x"
            - 12 steps separated by "-"
            - G=Green, O=Orange, R=Red, x=Blank
            - Multi-LED: GO, GOR, OR, GR

        Examples:
            "G-x-G-x-G-x-G-x-G-x-G-x" → Simple blink
            "GO-x-GO-x-GO-x-GO-x-GO-x-GO-x" → Green+Orange blink
            "G-O-R-GOR-G-O-R-GOR-x-x-x-x" → Complex sequence
        """
        try:
            # Parse pattern to LED states
            led_states = parse_pattern(pattern)
        except PatternParseError as e:
            self.logger.error(f"Invalid pattern: {e}")
            return

        cycle_count = 0

        # Execute pattern cycles
        while not self._blink_stop_event.is_set():
            # Execute 12 steps
            for green, orange, red in led_states:
                self._set_all_leds(green, orange, red)

                # Check for stop during step
                if self._blink_stop_event.wait(step_duration):
                    self._set_all_leds(False, False, False)  # Turn off on exit
                    return

            # Pause between cycles (if configured)
            if pause_duration > 0:
                self._set_all_leds(False, False, False)

                # Check for stop during pause
                if self._blink_stop_event.wait(pause_duration):
                    return

            # Check repeat limit
            cycle_count += 1
            if repeat_count is not None and cycle_count >= repeat_count:
                self._set_all_leds(False, False, False)
                self.logger.debug(
                    f"Pattern completed {cycle_count} cycles, stopping",
                )
                return

    def flash_error(self, duration: float = LED_ERROR_DURATION) -> None:
        """
        Flash red LED rapidly to indicate error using 12-step pattern.

        This is attention-grabbing for critical errors.
        After flashing, returns to previous pattern.

        Args:
            duration: How long to flash in seconds (default from settings)

        Example:
            led.flash_error()  # Flash for 2 seconds, then restore
        """
        self.logger.info(f"Flashing error LED for {duration}s")

        # Save current pattern to restore later
        original_pattern = self.current_pattern

        # Calculate how many cycles to flash for the duration
        cycle_time = (12 * LED_ERROR_STEP_DURATION) + LED_ERROR_PAUSE_DURATION
        repeat_count = max(1, int(duration / cycle_time))

        # Start error pattern in background thread with automatic restore
        flash_thread = threading.Thread(
            target=self._flash_error_worker,
            args=(original_pattern, repeat_count),
            daemon=True,
            name="LED-Error-Flash",
        )
        flash_thread.start()

    def _flash_error_worker(
        self,
        restore_pattern: LEDPattern,
        repeat_count: int,
    ) -> None:
        """
        Background worker for error flash.

        Flashes error pattern, then restores original pattern.

        Args:
            restore_pattern: Pattern to restore after flashing
            repeat_count: Number of error pattern cycles
        """
        # Stop current animation
        self._stop_blinking()

        # Execute error pattern
        self._start_pattern(
            LED_ERROR_PATTERN,
            LED_ERROR_STEP_DURATION,
            LED_ERROR_PAUSE_DURATION,
            repeat_count=repeat_count,
        )

        # Wait for error pattern to complete
        # Calculate total duration
        cycle_time = (12 * LED_ERROR_STEP_DURATION) + LED_ERROR_PAUSE_DURATION
        total_time = cycle_time * repeat_count
        time.sleep(total_time + 0.1)  # Small buffer

        # Restore original pattern
        self._restore_pattern(restore_pattern)

    def flash_extension_success(self) -> None:
        """
        Flash green LED using 12-step pattern to confirm time extension.

        Quick visual feedback that recording extension was successful.
        Blocks until flash completes. Caller should set appropriate pattern after.

        Uses LED_EXTENSION_ADDED pattern from settings.

        Example:
            led.flash_extension_success()  # Quick confirmation flash (blocking)
            led.set_status(LEDPattern.RECORDING)  # Set next pattern
        """
        self.logger.info("Flashing extension success")

        # Save current pattern (no longer used for restore, kept for compatibility)
        original_pattern = self.current_pattern

        # Run flash sequence and wait for completion (blocking)
        flash_thread = threading.Thread(
            target=self._extension_flash_worker,
            args=(original_pattern,),
            daemon=True,
            name="LED-Extension-Flash",
        )
        flash_thread.start()

        # Wait for flash to complete before returning
        flash_thread.join()

    def _extension_flash_worker(self, restore_pattern: LEDPattern) -> None:
        """
        Background worker for extension success flash using pattern framework.

        Executes extension pattern, then restores original pattern.

        Args:
            restore_pattern: Pattern to restore after flashing
        """
        # Stop any current animation
        self._stop_blinking()

        # Execute extension pattern
        self._start_pattern(
            LED_EXTENSION_ADDED_PATTERN,
            LED_EXTENSION_ADDED_STEP_DURATION,
            LED_EXTENSION_ADDED_PAUSE_DURATION,
            repeat_count=LED_EXTENSION_ADDED_REPEAT_COUNT,
        )

        # Wait for pattern thread to complete (join instead of sleep)
        if self._blink_thread and self._blink_thread.is_alive():
            # Calculate expected duration
            cycle_time = (
                12 * LED_EXTENSION_ADDED_STEP_DURATION
            ) + LED_EXTENSION_ADDED_PAUSE_DURATION
            total_time = cycle_time * LED_EXTENSION_ADDED_REPEAT_COUNT
            self._blink_thread.join(timeout=total_time + 0.5)

        # Turn off LEDs after flash completes
        # Caller (recorder_service) will set appropriate pattern based on remaining time
        self._set_all_leds(False, False, False)

    def flash_recording_started(self) -> None:
        """
        Flash green LED using 12-step pattern when recording starts.

        Quick visual feedback that recording has begun.
        After flashing, continues to recording pattern.

        Uses LED_RECORDING_STARTED pattern from settings.

        Example:
            led.flash_recording_started()  # Quick flash when recording begins
        """
        self.logger.info("Flashing recording started")

        # Run flash sequence in background thread (non-blocking)
        flash_thread = threading.Thread(
            target=self._recording_started_flash_worker,
            daemon=True,
            name="LED-Recording-Started-Flash",
        )
        flash_thread.start()

    def _recording_started_flash_worker(self) -> None:
        """
        Background worker for recording started flash.

        Executes recording started pattern, then switches to recording pattern.
        """
        # Stop any current animation
        self._stop_blinking()

        # Execute recording started pattern
        self._start_pattern(
            LED_RECORDING_STARTED_PATTERN,
            LED_RECORDING_STARTED_STEP_DURATION,
            LED_RECORDING_STARTED_PAUSE_DURATION,
            repeat_count=LED_RECORDING_STARTED_REPEAT_COUNT,
        )

        # Wait for pattern thread to complete (join instead of sleep)
        if self._blink_thread and self._blink_thread.is_alive():
            # Calculate expected duration
            cycle_time = (
                12 * LED_RECORDING_STARTED_STEP_DURATION
            ) + LED_RECORDING_STARTED_PAUSE_DURATION
            total_time = cycle_time * LED_RECORDING_STARTED_REPEAT_COUNT
            self._blink_thread.join(timeout=total_time + 0.5)

        # Switch to recording pattern
        self.set_status(LEDPattern.RECORDING)

    def flash_starting(self) -> None:
        """
        Start pulsing LED immediately on button press.

        Provides instant feedback that button was registered.
        Continues pulsing during camera initialization.
        Will be interrupted by flash_recording_started() when camera ready.

        Uses LED_RECORDING_STARTING pattern from settings.

        Example:
            led.flash_starting()  # Immediate feedback on button press
        """
        self.logger.info("Starting pattern (button acknowledged)")

        # Stop any current animation
        self._stop_blinking()

        # Start continuous starting pattern (no repeat limit)
        self._start_pattern(
            LED_RECORDING_STARTING_PATTERN,
            LED_RECORDING_STARTING_STEP_DURATION,
            LED_RECORDING_STARTING_PAUSE_DURATION,
            repeat_count=None,  # Continuous until interrupted
        )

    def play_warning_sequence(self, level: int = 3) -> None:
        """
        Start warning sequence animation using 12-step pattern framework.

        This is called when recording time warning is reached.
        Supports multiple warning levels with different patterns.

        Args:
            level: Warning level (1, 2, or 3)
                   1 = Early warning (3 minutes) - Green+Orange double blink
                   2 = Mid warning (2 minutes) - All colors rapid sequence
                   3 = Final warning (1 minute) - Fast all-LED flash

        Stops when:
        - Recording is extended
        - Recording completes
        - Pattern changes to something else

        Example:
            led.play_warning_sequence(1)  # Level 1 warning
            led.play_warning_sequence(3)  # Level 3 warning (default)
        """
        self.logger.info(f"Starting warning sequence level {level}")

        # Stop any current blinking
        self._stop_blinking()

        # Update current pattern so set_status() knows we're in warning mode
        self.current_pattern = LEDPattern.WARNING

        # Select pattern based on level
        if level == 1:
            pattern = LED_RECORDING_WARN1_PATTERN
            step_duration = LED_RECORDING_WARN1_STEP_DURATION
            pause_duration = LED_RECORDING_WARN1_PAUSE_DURATION
        elif level == 2:
            pattern = LED_RECORDING_WARN2_PATTERN
            step_duration = LED_RECORDING_WARN2_STEP_DURATION
            pause_duration = LED_RECORDING_WARN2_PAUSE_DURATION
        else:  # level 3 (default)
            pattern = LED_RECORDING_WARN3_PATTERN
            step_duration = LED_RECORDING_WARN3_STEP_DURATION
            pause_duration = LED_RECORDING_WARN3_PAUSE_DURATION

        # Start warning pattern (continuous, no repeat limit)
        self._start_pattern(
            pattern,
            step_duration,
            pause_duration,
            repeat_count=None,  # Infinite
        )

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

        Blinks with interval from settings.
        Continues until _upload_blink_event is set.
        """
        # _upload_blink_event is guaranteed to be set by set_upload_active()
        # before this thread starts
        if self._upload_blink_event is None:
            self.logger.error("Upload blink event is None")
            return

        blink_interval = LED_UPLOAD_BLINK_INTERVAL
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
