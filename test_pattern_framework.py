#!/usr/bin/env python3
"""
Test LED Pattern Framework

Tests the new 12-step pattern system for LED animations.
Validates pattern parsing, configuration loading, and pattern execution.

Usage:
    python test_pattern_framework.py
"""

import logging
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import (
    LED_ERROR_PATTERN,
    LED_EXTENSION_ADDED_PATTERN,
    LED_RECORDING_PATTERN,
    LED_RECORDING_STARTED_PATTERN,
    LED_RECORDING_WARN1_PATTERN,
    LED_RECORDING_WARN2_PATTERN,
    LED_RECORDING_WARN3_PATTERN,
)
from hardware.constants import LEDPattern
from hardware.controllers.led_controller import LEDController
from hardware.utils import get_pattern_info, validate_pattern

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s | %(name)s | %(levelname)s",
)
logger = logging.getLogger(__name__)


def test_pattern_validation():
    """Test pattern validation and parsing."""
    logger.info("=" * 60)
    logger.info("TEST 1: Pattern Validation")
    logger.info("=" * 60)

    test_patterns = {
        "Recording": LED_RECORDING_PATTERN,
        "Recording Started": LED_RECORDING_STARTED_PATTERN,
        "Warning Level 1": LED_RECORDING_WARN1_PATTERN,
        "Warning Level 2": LED_RECORDING_WARN2_PATTERN,
        "Warning Level 3": LED_RECORDING_WARN3_PATTERN,
        "Extension Added": LED_EXTENSION_ADDED_PATTERN,
        "Error": LED_ERROR_PATTERN,
    }

    all_valid = True
    for name, pattern in test_patterns.items():
        valid, error = validate_pattern(pattern)
        if valid:
            info = get_pattern_info(pattern)
            logger.info(
                f"✓ {name:20s}: {pattern[:30]:30s}... "
                f"G={info['green_steps']} O={info['orange_steps']} "
                f"R={info['red_steps']} Blank={info['blank_steps']}",
            )
        else:
            logger.error(f"✗ {name:20s}: INVALID - {error}")
            all_valid = False

    logger.info("")
    if all_valid:
        logger.info("✓ All patterns are valid!")
    else:
        logger.error("✗ Some patterns are invalid")
        return False

    return True


def test_pattern_execution():
    """Test pattern execution with LED controller."""
    logger.info("=" * 60)
    logger.info("TEST 2: Pattern Execution")
    logger.info("=" * 60)

    try:
        with LEDController() as led:
            # Test 1: Recording pattern
            logger.info("Testing recording pattern (3 seconds)...")
            led.set_status(LEDPattern.RECORDING)
            time.sleep(3)

            # Test 2: Recording started flash
            logger.info("Testing recording started flash...")
            led.flash_recording_started()
            time.sleep(2)

            # Test 3: Extension flash
            logger.info("Testing extension added flash...")
            led.flash_extension_success()
            time.sleep(2)

            # Test 4: Warning level 1
            logger.info("Testing warning level 1 (3 seconds)...")
            led.play_warning_sequence(level=1)
            time.sleep(3)

            # Test 5: Warning level 2
            logger.info("Testing warning level 2 (3 seconds)...")
            led.play_warning_sequence(level=2)
            time.sleep(3)

            # Test 6: Warning level 3
            logger.info("Testing warning level 3 (3 seconds)...")
            led.play_warning_sequence(level=3)
            time.sleep(3)

            # Test 7: Error flash
            logger.info("Testing error flash...")
            led.flash_error()
            time.sleep(3)

            # Test 8: Static patterns
            logger.info("Testing static patterns...")
            led.set_status(LEDPattern.READY)
            time.sleep(1)
            led.set_status(LEDPattern.PROCESSING)
            time.sleep(1)
            led.set_status(LEDPattern.ERROR)
            time.sleep(1)

            # Cleanup
            logger.info("Turning off LEDs...")
            led.set_status(LEDPattern.OFF)

        logger.info("")
        logger.info("✓ Pattern execution completed successfully!")
        return True

    except Exception as e:
        logger.error(f"✗ Pattern execution failed: {e}", exc_info=True)
        return False


def main():
    """Run all tests."""
    logger.info("")
    logger.info("LED PATTERN FRAMEWORK TEST")
    logger.info("=" * 60)
    logger.info("")

    # Test 1: Validation
    if not test_pattern_validation():
        logger.error("")
        logger.error("Pattern validation failed - aborting execution test")
        return 1

    # Test 2: Execution
    logger.info("")
    response = input("Run LED execution test? (y/N): ")
    if response.lower() == "y":
        if not test_pattern_execution():
            return 1
    else:
        logger.info("Skipping execution test")

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("✓ ALL TESTS PASSED!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Pattern framework is ready to use.")
    logger.info("Edit patterns in config/settings.py to customize animations.")
    logger.info("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
