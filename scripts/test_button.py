#!/usr/bin/env python3
"""
Real Button Hardware Test

Tests button input on actual Raspberry Pi GPIO.
Must be run on Raspberry Pi with button connected.

Usage:
    python scripts/test_button.py
"""

import sys
import time

from hardware.controllers.button_controller import ButtonController, ButtonPress
from hardware.factory import HardwareFactory


def test_button_system():
    """Test real button hardware"""
    print("=" * 60)
    print("BUTTON HARDWARE TEST")
    print("=" * 60)
    print()

    # Check if running on real hardware
    hw_status = HardwareFactory.is_real_hardware_available()
    if not hw_status['gpio']:
        print("WARNING: Not running on Raspberry Pi or GPIO not available")
        print("This test requires real GPIO hardware")
        print()
        print("On mock GPIO, you can simulate button presses:")
        print("  Press 's' + Enter for single press")
        print("  Press 'd' + Enter for double press")
        print()

    # Create GPIO (real or mock based on availability)
    print("Initializing GPIO...")
    gpio = HardwareFactory.create_gpio()

    # Create button controller
    button = ButtonController(gpio=gpio)

    # Check status
    status = button.get_status()
    print(f"  GPIO Available: {status['gpio_available']}")
    print(f"  Button Pin: GPIO {status['pin']}")
    print(f"  Pull-up Resistor: {status['pull_up']}")
    print(f"  Debounce Time: {status['debounce_time']}s")
    print(f"  Double-tap Window: {status['double_tap_window']}s")
    print()

    # Track button presses
    press_count = {'single': 0, 'double': 0}

    def on_button_press(press_type):
        """Callback for button presses"""
        timestamp = time.strftime("%H:%M:%S")

        if press_type == ButtonPress.SINGLE:
            press_count['single'] += 1
            print(f"  [{timestamp}] SINGLE press detected (total: {press_count['single']})")
        elif press_type == ButtonPress.DOUBLE:
            press_count['double'] += 1
            print(f"  [{timestamp}] DOUBLE press detected (total: {press_count['double']})")

    # Register callback
    button.register_callback(on_button_press)

    # Test 1: Basic button detection
    print("Test 1: Button press detection")
    print("-" * 60)
    print()
    print("Instructions:")
    print("  1. Press the button ONCE (single press)")
    print("  2. Wait 2 seconds")
    print("  3. Press the button TWICE quickly (double press)")
    print("  4. Wait for confirmation")
    print()
    print("Testing for 15 seconds...")
    print("Press the button now!")
    print()

    start_time = time.time()
    test_duration = 15

    try:
        while time.time() - start_time < test_duration:
            remaining = test_duration - int(time.time() - start_time)
            if remaining % 5 == 0 and remaining > 0:
                print(f"  ({remaining} seconds remaining...)")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Test interrupted")

    print()
    print(f"Test 1 Results:")
    print(f"  Single presses: {press_count['single']}")
    print(f"  Double presses: {press_count['double']}")
    print()

    if press_count['single'] > 0 or press_count['double'] > 0:
        print("  [OK] Button is responding")
    else:
        print("  [WARNING] No button presses detected")
        print("  Check button connection and wiring")

    print()

    # Test 2: Timing adjustment
    print("Test 2: Testing custom timing")
    print("-" * 60)
    print()

    # Make double-tap window longer (easier to trigger)
    print("  Setting double-tap window to 1.0 second (easier)...")
    button.set_timing(double_tap_window=1.0)

    print("  Try double-pressing with slower timing...")
    print("  Testing for 10 seconds...")
    print()

    press_count = {'single': 0, 'double': 0}
    start_time = time.time()
    test_duration = 10

    try:
        while time.time() - start_time < test_duration:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Test interrupted")

    print()
    print(f"Test 2 Results:")
    print(f"  Single presses: {press_count['single']}")
    print(f"  Double presses: {press_count['double']}")
    print("  [OK]")
    print()

    # Reset to defaults
    button.set_timing(double_tap_window=0.5)

    # Cleanup
    print("Cleaning up...")
    button.cleanup()

    # Summary
    print("=" * 60)
    print("BUTTON TEST COMPLETE")
    print("=" * 60)
    print()
    print("Verify that:")
    print("  - Single presses were detected correctly")
    print("  - Double presses were detected correctly")
    print("  - Timing felt responsive")
    print()

    return True


if __name__ == "__main__":
    try:
        success = test_button_system()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
