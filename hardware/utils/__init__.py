"""
Hardware Utilities Package

Exposes shared utility functions for hardware operations.

Public API:
    GPIO utilities:
    - check_gpio_available: Check if GPIO hardware is available
    - safe_gpio_cleanup: Safe GPIO pin cleanup with error handling
    - setup_led_pins: Configure LED pins for output
    - toggle_pin: Toggle pin state (HIGH <-> LOW)
    - set_pin_state: Set pin to specific state
    - read_pin_as_bool: Read pin state as boolean
    - validate_pin_number: Validate GPIO pin number

    Pattern utilities:
    - parse_pattern: Parse 12-step LED pattern string to states
    - validate_pattern: Validate pattern format
    - get_pattern_info: Get pattern statistics
    - PatternParseError: Exception for invalid patterns

Usage:
    from hardware.utils import parse_pattern, validate_pattern

    pattern = "G-x-G-x-G-x-G-x-G-x-G-x"
    is_valid, error = validate_pattern(pattern)
    if is_valid:
        states = parse_pattern(pattern)
"""

from hardware.utils.gpio_utils import (
    check_gpio_available,
    read_pin_as_bool,
    safe_gpio_cleanup,
    set_pin_state,
    setup_led_pins,
    toggle_pin,
    validate_pin_number,
)
from hardware.utils.pattern_parser import (
    PatternParseError,
    get_pattern_info,
    parse_pattern,
    validate_pattern,
)

# Public API
__all__ = [
    # Exception classes (capitalized, sorted first)
    "PatternParseError",
    # Functions (sorted alphabetically)
    "check_gpio_available",
    "get_pattern_info",
    "parse_pattern",
    "read_pin_as_bool",
    "safe_gpio_cleanup",
    "set_pin_state",
    "setup_led_pins",
    "toggle_pin",
    "validate_pattern",
    "validate_pin_number",
]
