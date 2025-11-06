#!/usr/bin/env python3
"""
LED Hardware Test Script

Tests all 3 LEDs to verify wiring and brightness consistency.
Run this after wiring to ensure everything works correctly.

Usage:
    sudo python3 test_led.py
"""
import time

# Import GPIO pin configuration from project settings
from config.settings import GPIO_LED_GREEN, GPIO_LED_ORANGE, GPIO_LED_RED

try:
    import RPi.GPIO as GPIO

    # Setup GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # Pin assignments from config/settings.py
    LED_GREEN = GPIO_LED_GREEN
    LED_ORANGE = GPIO_LED_ORANGE
    LED_RED = GPIO_LED_RED

    print("=" * 60)
    print("LED Hardware Test - All Hardware PWM Pins")
    print("=" * 60)
    print(f"Green LED:  GPIO {LED_GREEN} (Physical pin 33)")
    print(f"Orange LED: GPIO {LED_ORANGE} (Physical pin 32)")
    print(f"Red LED:    GPIO {LED_RED} (Physical pin 35)")
    print("=" * 60)
    print()

    # Setup all pins as output
    GPIO.setup(LED_GREEN, GPIO.OUT)
    GPIO.setup(LED_ORANGE, GPIO.OUT)
    GPIO.setup(LED_RED, GPIO.OUT)

    # Ensure all start OFF
    GPIO.output(LED_GREEN, GPIO.LOW)
    GPIO.output(LED_ORANGE, GPIO.LOW)
    GPIO.output(LED_RED, GPIO.LOW)

    print("Phase 1: Testing each LED individually")
    print("-" * 60)

    # Test Green
    print("\n1. GREEN LED - Should turn ON for 2 seconds")
    GPIO.output(LED_GREEN, GPIO.HIGH)
    time.sleep(2)
    print("   GREEN LED - Should turn OFF")
    GPIO.output(LED_GREEN, GPIO.LOW)
    time.sleep(1)

    # Test Orange
    print("\n2. ORANGE LED - Should turn ON for 2 seconds")
    GPIO.output(LED_ORANGE, GPIO.HIGH)
    time.sleep(2)
    print("   ORANGE LED - Should turn OFF")
    GPIO.output(LED_ORANGE, GPIO.LOW)
    time.sleep(1)

    # Test Red
    print("\n3. RED LED - Should turn ON for 2 seconds")
    GPIO.output(LED_RED, GPIO.HIGH)
    time.sleep(2)
    print("   RED LED - Should turn OFF")
    GPIO.output(LED_RED, GPIO.LOW)
    time.sleep(1)

    print("\n" + "=" * 60)
    print("Phase 2: Blinking sequence (3 times each)")
    print("-" * 60)

    for i in range(3):
        print(f"\nBlink {i+1}/3...")
        # Green blink
        GPIO.output(LED_GREEN, GPIO.HIGH)
        time.sleep(0.3)
        GPIO.output(LED_GREEN, GPIO.LOW)
        time.sleep(0.2)

        # Orange blink
        GPIO.output(LED_ORANGE, GPIO.HIGH)
        time.sleep(0.3)
        GPIO.output(LED_ORANGE, GPIO.LOW)
        time.sleep(0.2)

        # Red blink
        GPIO.output(LED_RED, GPIO.HIGH)
        time.sleep(0.3)
        GPIO.output(LED_RED, GPIO.LOW)
        time.sleep(0.2)

    print("\n" + "=" * 60)
    print("Phase 3: Brightness comparison")
    print("-" * 60)
    print("\nAll LEDs ON simultaneously for 3 seconds")
    print("Check if brightness looks EVEN across all 3 LEDs...")

    GPIO.output(LED_GREEN, GPIO.HIGH)
    GPIO.output(LED_ORANGE, GPIO.HIGH)
    GPIO.output(LED_RED, GPIO.HIGH)
    time.sleep(3)

    print("\nAll LEDs OFF")
    GPIO.output(LED_GREEN, GPIO.LOW)
    GPIO.output(LED_ORANGE, GPIO.LOW)
    GPIO.output(LED_RED, GPIO.LOW)

    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)
    print("\nExpected results:")
    print("✓ All LEDs turned on/off correctly")
    print("✓ All LEDs have similar brightness")
    print("✓ No LEDs stuck on or off")
    print("\nIf any LED didn't work, check:")
    print("- Wire connections to correct GPIO pins")
    print("- LED orientation (not backwards)")
    print("- GND connections secure")
    print()

    GPIO.cleanup()

except KeyboardInterrupt:
    print("\n\nTest interrupted by user")
    GPIO.cleanup()
except ImportError:
    print("ERROR: RPi.GPIO library not found!")
    print("This script must run on a Raspberry Pi with RPi.GPIO installed")
    print("Install with: pip3 install RPi.GPIO")
except Exception as e:
    print(f"\nERROR: {e}")
    GPIO.cleanup()
