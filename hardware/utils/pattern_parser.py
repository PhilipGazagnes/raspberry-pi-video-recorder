"""
LED Pattern Parser

Parses 12-step pattern strings into LED state sequences.
Provides validation and conversion utilities for the pattern framework.

Pattern Format:
    "G-O-R-GOR-x-x-G-O-R-GOR-x-x"

    - 12 steps separated by "-"
    - Each step defines which LEDs are on
    - G = Green, O = Orange, R = Red
    - x or _ = Blank (all off)
    - Combinations: GO, GOR, OR, GR, etc.

Examples:
    "G-x-G-x-G-x-G-x-G-x-G-x"           → Simple green blink
    "GO-x-GO-x-GO-x-GO-x-GO-x-GO-x"     → Green+Orange blink
    "G-O-R-GOR-G-O-R-GOR-x-x-x-x"       → Complex sequence
    "GGG-x-x-x-GGG-x-x-x-x-x-x-x"       → Double pulse

Author: Pattern Framework
Date: 2025-11-21
"""

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


class PatternParseError(ValueError):
    """Raised when pattern string is invalid."""


def parse_pattern(pattern: str) -> List[Tuple[bool, bool, bool]]:
    """
    Parse pattern string to list of LED states.

    Args:
        pattern: 12-step pattern string (e.g., "G-x-G-x-G-x-G-x-G-x-G-x")

    Returns:
        List of 12 tuples, each containing (green, orange, red) boolean states

    Raises:
        PatternParseError: If pattern format is invalid

    Example:
        >>> parse_pattern("G-O-R-GOR-x-x-G-O-R-GOR-x-x")
        [
            (True, False, False),   # G
            (False, True, False),   # O
            (False, False, True),   # R
            (True, True, True),     # GOR
            (False, False, False),  # x
            (False, False, False),  # x
            (True, False, False),   # G
            (False, True, False),   # O
            (False, False, True),   # R
            (True, True, True),     # GOR
            (False, False, False),  # x
            (False, False, False),  # x
        ]
    """
    # Split pattern into steps
    steps = pattern.split("-")

    # Validate step count
    if len(steps) != 12:
        raise PatternParseError(
            f"Pattern must have exactly 12 steps, got {len(steps)}: '{pattern}'",
        )

    # Parse each step
    led_states = []
    for i, step in enumerate(steps):
        try:
            green, orange, red = _parse_step(step)
            led_states.append((green, orange, red))
        except ValueError as e:
            raise PatternParseError(
                f"Invalid step {i+1}/12 ('{step}'): {e}",
            ) from e

    return led_states


def _parse_step(step: str) -> Tuple[bool, bool, bool]:
    """
    Parse a single step to LED states.

    Args:
        step: Step string (e.g., "G", "GO", "GOR", "x", "_")

    Returns:
        Tuple of (green, orange, red) booleans

    Raises:
        ValueError: If step contains invalid characters

    Examples:
        >>> _parse_step("G")
        (True, False, False)
        >>> _parse_step("GO")
        (True, True, False)
        >>> _parse_step("GOR")
        (True, True, True)
        >>> _parse_step("x")
        (False, False, False)
    """
    # Normalize step
    step = step.strip().upper()

    # Handle blank/off states
    if step in ("X", "_", ""):
        return (False, False, False)

    # Validate characters
    valid_chars = {"G", "O", "R"}
    invalid_chars = set(step) - valid_chars
    if invalid_chars:
        raise ValueError(
            f"Invalid characters: {invalid_chars}. Use G, O, R, x, or _",
        )

    # Parse LED states
    green = "G" in step
    orange = "O" in step
    red = "R" in step

    return (green, orange, red)


def validate_pattern(pattern: str) -> Tuple[bool, str]:
    """
    Validate pattern string without raising exceptions.

    Args:
        pattern: Pattern string to validate

    Returns:
        Tuple of (is_valid, error_message)
        - If valid: (True, "")
        - If invalid: (False, "error description")

    Example:
        >>> validate_pattern("G-x-G-x-G-x-G-x-G-x-G-x")
        (True, "")
        >>> validate_pattern("G-O-R")
        (False, "Pattern must have exactly 12 steps, got 3: 'G-O-R'")
    """
    try:
        parse_pattern(pattern)
        return (True, "")
    except PatternParseError as e:
        return (False, str(e))


def pattern_to_string(led_states: List[Tuple[bool, bool, bool]]) -> str:
    """
    Convert LED state list back to pattern string.

    Useful for debugging or configuration generation.

    Args:
        led_states: List of 12 (green, orange, red) tuples

    Returns:
        Pattern string

    Example:
        >>> states = [(True, False, False), (False, False, False)] * 6
        >>> pattern_to_string(states)
        "G-x-G-x-G-x-G-x-G-x-G-x"
    """
    steps = []
    for green, orange, red in led_states:
        if not any([green, orange, red]):
            steps.append("x")
        else:
            step = ""
            if green:
                step += "G"
            if orange:
                step += "O"
            if red:
                step += "R"
            steps.append(step)

    return "-".join(steps)


def get_pattern_info(pattern: str) -> dict:
    """
    Get human-readable information about a pattern.

    Args:
        pattern: Pattern string

    Returns:
        Dictionary with pattern analysis:
        - valid: bool
        - error: str (empty if valid)
        - step_count: int
        - green_steps: int (steps with green LED on)
        - orange_steps: int (steps with orange LED on)
        - red_steps: int (steps with red LED on)
        - blank_steps: int (steps with all LEDs off)
        - multi_led_steps: int (steps with multiple LEDs)

    Example:
        >>> info = get_pattern_info("G-O-R-GOR-x-x-G-O-R-GOR-x-x")
        >>> info['green_steps']
        6
        >>> info['multi_led_steps']
        2
    """
    valid, error = validate_pattern(pattern)

    if not valid:
        return {
            "valid": False,
            "error": error,
            "step_count": 0,
            "green_steps": 0,
            "orange_steps": 0,
            "red_steps": 0,
            "blank_steps": 0,
            "multi_led_steps": 0,
        }

    led_states = parse_pattern(pattern)

    green_count = sum(1 for g, o, r in led_states if g)
    orange_count = sum(1 for g, o, r in led_states if o)
    red_count = sum(1 for g, o, r in led_states if r)
    blank_count = sum(1 for g, o, r in led_states if not any([g, o, r]))
    multi_led_count = sum(1 for g, o, r in led_states if sum([g, o, r]) > 1)

    return {
        "valid": True,
        "error": "",
        "step_count": len(led_states),
        "green_steps": green_count,
        "orange_steps": orange_count,
        "red_steps": red_count,
        "blank_steps": blank_count,
        "multi_led_steps": multi_led_count,
    }
