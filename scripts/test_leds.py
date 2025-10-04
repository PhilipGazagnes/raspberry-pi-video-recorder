#!/usr/bin/env python3
"""
Real LED Hardware Test

Tests LED control on actual Raspberry Pi GPIO.
Must be run on Raspberry Pi with LEDs connected.

Usage:
    python scripts/test_leds.py
"""

import sys
import time

from hardware.constants import LEDPattern
from hardware.controllers.led_controller import LEDController
from hardware.factory import HardwareFactory


def test_led_system():
    """Test real LED hardware"""
    print("=" * 60)
    print("LED HARDWARE TEST")
    print("=" * 60)
    print()

    # Check if running on real hardware
    hw_status = HardwareFactory.is_real_hardware_available()
    if not hw_status['gpio']:
        print("WARNING: Not running on Raspberry Pi or GPIO not available")
        print("This test requires real GPIO hardware")
        print()
        response = input("Continue anyway with mock? (y/n): ")
        if response.lower() != 'y':
            return False

    # Create GPIO (real or mock based on availability)
    print("Initializing GPIO...")
    gpio = HardwareFactory.create_gpio()

    # Create LED controller
    led = LEDController(gpio=gpio)

    # Check status
    status = led.get_status()
    print(f"  GPIO Available: {status['gpio_available']}")
    print(f"  Current Pattern: {status['current_pattern']}")
    print(f"  Pin Configuration:")
    print(f"    Green:  GPIO {status['pins']['green']}")
    print(f"    Orange: GPIO {status['pins']['orange']}")
    print(f"    Red:    GPIO {status['pins']['red']}")
    print()

    # Test 1: Individual LEDs
    print("Test 1: Testing individual LED patterns...")
    print("  Watch the LEDs change state")
    print()

    patterns = [
        (LEDPattern.OFF, "All OFF", 1),
        (LEDPattern.READY, "Green ON (READY)", 2),
        (LEDPattern.PROCESSING, "Orange ON (PROCESSING)", 2),
        (LEDPattern.ERROR, "Red ON (ERROR)", 2),
        (LEDPattern.OFF, "All OFF", 1),
    ]

    for pattern, description, duration in patterns:
        print(f"  {description}...")
        led.set_status(pattern)
        time.sleep(duration)
        print(f"    [OK]")

    print()

    # Test 2: Blinking pattern
    print("Test 2: Testing blinking pattern...")
    print("  Green LED should blink for 5 seconds (RECORDING)")
    led.set_status(LEDPattern.RECORDING)
    time.sleep(5)
    print("  [OK]")
    print()

    # Turn off
    led.set_status(LEDPattern.OFF)
    time.sleep(0.5)

    # Test 3: Error flash
    print("Test 3: Testing error flash...")
    print("  Starting in READY state (green solid)")
    led.set_status(LEDPattern.READY)
    time.sleep(1)

    print("  Flashing error (red rapid blink for 2 seconds)...")
    led.flash_error(duration=2.0)
    time.sleep(2.5)

    print("  Should return to green solid")
    time.sleep(1)
    print("  [OK]")
    print()

    # Test 4: Full sequence (simulating real usage)
    print("Test 4: Testing full recording sequence...")
    print("  This simulates the LEDs during actual system operation")
    print()

    sequence = [
        (LEDPattern.READY, "System ready - Green solid", 2),
        (LEDPattern.RECORDING, "Recording - Green blinking", 3),
        (LEDPattern.PROCESSING, "Processing/Uploading - Orange solid", 2),
        (LEDPattern.READY, "Ready for next - Green solid", 2),
    ]

    for pattern, description, duration in sequence:
        print(f"  {description}")
        led.set_status(pattern)
        time.sleep(duration)

    print("  [OK]")
    print()

    # Test 5: Test sequence method
    print("Test 5: Running built-in test sequence...")
    print("  Watch LEDs cycle through all patterns")
    led.test_sequence(duration_per_step=1.5)
    print("  [OK]")
    print()

    # Cleanup
    print("Cleaning up (all LEDs OFF)...")
    led.cleanup()
    time.sleep(0.5)

    # Summary
    print("=" * 60)
    print("LED TEST COMPLETE")
    print("=" * 60)
    print()
    print("Verify that:")
    print("  - Green LED lit up correctly")
    print("  - Orange LED lit up correctly")
    print("  - Red LED lit up correctly")
    print("  - Green LED blinked smoothly")
    print("  - All LEDs turned off at the end")
    print()

    return True


if __name__ == "__main__":
    try:
        success = test_led_system()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        print("Cleaning up...")
        # Try to turn off LEDs
        try:
            gpio = HardwareFactory.create_gpio()
            led = LEDController(gpio=gpio)
            led.cleanup()
        except:
            pass
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
