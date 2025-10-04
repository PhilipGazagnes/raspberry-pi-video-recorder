"""
GPIO Utilities

Shared utility functions for GPIO operations.
Extracted here to follow DRY (Don't Repeat Yourself) principle.

These are helper functions used by multiple controllers,
so they live in one place instead of being duplicated.
"""

import logging
from typing import Optional

from hardware.interfaces.gpio_interface import GPIOInterface, PinState


def safe_gpio_cleanup(
    gpio: Optional[GPIOInterface],
    pins: Optional[list[int]] = None,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Safely clean up GPIO pins with error handling.

    This is a common pattern - cleanup should never crash your program,
    even if something goes wrong. This helper ensures safe cleanup.

    Args:
        gpio: GPIO interface to clean up, or None
        pins: Specific pins to clean, or None for all
        logger: Optional logger for error messages

    Example:
        safe_gpio_cleanup(self.gpio, [12, 16, 20], self.logger)
    """
    if gpio is None:
        return

    try:
        gpio.cleanup(pins)
    except Exception as e:
        if logger:
            logger.error(f"Error during GPIO cleanup: {e}")
        # Don't raise - cleanup should be forgiving


def toggle_pin(
    gpio: GPIOInterface,
    pin: int,
    current_state: PinState
) -> PinState:
    """
    Toggle a pin's state (HIGH -> LOW or LOW -> HIGH).

    Useful for LED blinking logic.

    Args:
        gpio: GPIO interface
        pin: Pin number to toggle
        current_state: Current state of the pin

    Returns:
        New state after toggle

    Example:
        new_state = toggle_pin(self.gpio, 12, old_state)
    """
    new_state = PinState.LOW if current_state == PinState.HIGH else PinState.HIGH
    gpio.write(pin, new_state)
    return new_state


def set_pin_state(
    gpio: GPIOInterface,
    pin: int,
    state: bool
) -> None:
    """
    Set pin state using boolean (True=HIGH, False=LOW).

    More intuitive than PinState enum for simple on/off logic.

    Args:
        gpio: GPIO interface
        pin: Pin number
        state: True for HIGH, False for LOW

    Example:
        set_pin_state(self.gpio, 12, True)  # Turn LED on
    """
    pin_state = PinState.HIGH if state else PinState.LOW
    gpio.write(pin, pin_state)


def read_pin_as_bool(
    gpio: GPIOInterface,
    pin: int
) -> bool:
    """
    Read pin state as boolean (HIGH=True, LOW=False).

    More intuitive than PinState enum for simple checks.

    Args:
        gpio: GPIO interface
        pin: Pin number

    Returns:
        True if HIGH, False if LOW

    Example:
        if read_pin_as_bool(self.gpio, 18):
            print("Button is pressed")
    """
    state = gpio.read(pin)
    return state == PinState.HIGH


def setup_led_pins(
    gpio: GPIOInterface,
    pins: list[int],
    initial_state: PinState = PinState.LOW
) -> None:
    """
    Set up multiple LED pins at once.

    Common pattern for LED controllers - initialize all LEDs in one call.

    Args:
        gpio: GPIO interface
        pins: List of pin numbers to set up
        initial_state: Starting state for all pins (default: LOW/off)

    Example:
        setup_led_pins(self.gpio, [12, 16, 20], PinState.LOW)
    """
    for pin in pins:
        gpio.setup_output(pin)
        gpio.write(pin, initial_state)


def check_gpio_available(
    gpio: GPIOInterface,
    logger: Optional[logging.Logger] = None
) -> bool:
    """
    Check if GPIO hardware is available and log appropriate message.

    Args:
        gpio: GPIO interface to check
        logger: Optional logger for messages

    Returns:
        True if real hardware available, False if simulated
    """
    is_available = gpio.is_available()

    if logger:
        if is_available:
            logger.info("Running on real GPIO hardware")
        else:
            logger.warning("Running in GPIO simulation mode")

    return is_available


def validate_pin_number(pin: int, min_pin: int = 0, max_pin: int = 27) -> None:
    """
    Validate GPIO pin number is in valid range.

    Raspberry Pi 5 has GPIO pins 0-27 in BCM mode.

    Args:
        pin: Pin number to validate
        min_pin: Minimum valid pin number (default: 0)
        max_pin: Maximum valid pin number (default: 27)

    Raises:
        ValueError: If pin number is invalid

    Example:
        validate_pin_number(18)  # OK
        validate_pin_number(99)  # Raises ValueError
    """
    if not isinstance(pin, int):
        raise ValueError(f"Pin must be an integer, got {type(pin)}")

    if pin < min_pin or pin > max_pin:
        raise ValueError(
            f"Invalid pin number: {pin}. "
            f"Must be between {min_pin} and {max_pin}"
        )
