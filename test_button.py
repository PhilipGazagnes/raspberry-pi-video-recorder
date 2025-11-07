#!/usr/bin/env python3
"""
Button Hardware Test Script

Tests the button to verify wiring and detect presses.
Press Ctrl+C to exit.

Usage:
    sudo python3 test_button.py
"""
import time

# Import GPIO pin configuration from project settings
from config.settings import GPIO_BUTTON_PIN

try:
    from RPi import GPIO

    # Setup GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Button configuration from config/settings.py
    BUTTON_PIN = GPIO_BUTTON_PIN

    print("=" * 60)
    print("Button Hardware Test")
    print("=" * 60)
    print(f"Button: GPIO {BUTTON_PIN} (Physical pin 12)")
    print("=" * 60)
    print()
    print("Instructions:")
    print("1. Press the button - you should see 'PRESSED' and 'RELEASED'")
    print("2. Try single presses and double presses")
    print("3. Press Ctrl+C to exit")
    print()
    print("Waiting for button presses...")
    print("-" * 60)

    # Setup button pin as input with pull-up resistor
    # Pull-up means: button pressed = LOW, button released = HIGH
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    # Track button state
    last_state = GPIO.HIGH  # Start with "not pressed" state
    press_count = 0

    while True:
        # Read current button state
        current_state = GPIO.input(BUTTON_PIN)

        # Detect state change
        if current_state != last_state:
            if current_state == GPIO.LOW:
                # Button pressed (LOW because of pull-up)
                press_count += 1
                print(f"[{time.strftime('%H:%M:%S')}] ✓ PRESSED (count: {press_count})")
            else:
                # Button released
                print(f"[{time.strftime('%H:%M:%S')}]   RELEASED")

            last_state = current_state

        # Small delay to avoid busy-waiting and allow CPU to do other things
        time.sleep(0.01)  # 10ms polling rate

except KeyboardInterrupt:
    print("\n\n" + "=" * 60)
    print(f"Test complete! Total presses detected: {press_count}")
    print("=" * 60)
    print("\nExpected results:")
    print("✓ Button presses are detected immediately")
    print("✓ Each press shows 'PRESSED' then 'RELEASED'")
    print("✓ No false triggers or bouncing")
    print("\nIf button didn't work, check:")
    print("- Wire from button to GPIO 18 (pin 12)")
    print("- Wire from button to GND (pin 14 or any GND)")
    print("- Button is working (not broken)")
    print()
    GPIO.cleanup()

except ImportError:
    print("ERROR: RPi.GPIO library not found!")
    print("This script must run on a Raspberry Pi with RPi.GPIO installed")
    print("Install with: pip3 install RPi.GPIO")

except Exception as e:
    print(f"\nERROR: {e}")
    GPIO.cleanup()
