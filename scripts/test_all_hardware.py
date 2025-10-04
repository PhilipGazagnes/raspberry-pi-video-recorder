#!/usr/bin/env python3
"""
Comprehensive Hardware Smoke Test

Tests all hardware components (LEDs, Button, Audio) in sequence.
Run before deploying to verify all hardware is working.

Usage:
    python scripts/test_all_hardware.py
"""

import sys
import time

from hardware.constants import AudioMessage, LEDPattern
from hardware.controllers import AudioController, ButtonController, LEDController
from hardware.factory import HardwareFactory


class HardwareTestSuite:
    """Comprehensive hardware testing suite"""

    def __init__(self):
        self.passed_tests = []
        self.failed_tests = []

    def run_all_tests(self):
        """Run all hardware tests"""
        print("=" * 70)
        print(" " * 15 + "HARDWARE SMOKE TEST SUITE")
        print("=" * 70)
        print()

        # Check hardware availability
        self._check_hardware_availability()
        print()

        # Run individual test suites
        tests = [
            ("Audio System", self._test_audio),
            ("LED System", self._test_leds),
            ("Button System", self._test_button),
        ]

        for test_name, test_func in tests:
            print("-" * 70)
            print(f"TESTING: {test_name}")
            print("-" * 70)
            print()

            try:
                test_func()
                self.passed_tests.append(test_name)
                print(f"[PASS] {test_name}")
            except Exception as e:
                self.failed_tests.append((test_name, str(e)))
                print(f"[FAIL] {test_name}: {e}")

            print()
            time.sleep(1)

        # Print summary
        self._print_summary()

        return len(self.failed_tests) == 0

    def _check_hardware_availability(self):
        """Check which hardware is available"""
        print("Checking hardware availability...")
        hw_status = HardwareFactory.is_real_hardware_available()

        print(f"  GPIO: {'Available' if hw_status['gpio'] else 'Mock mode'}")
        print(f"  TTS:  {'Available' if hw_status['tts'] else 'Mock mode'}")

        if not hw_status['gpio']:
            print()
            print("  WARNING: Running without real GPIO hardware")
            print("  LED and Button tests will use simulation mode")

        if not hw_status['tts']:
            print()
            print("  WARNING: Running without real TTS")
            print("  Audio test will use simulation mode")

    def _test_audio(self):
        """Test audio system"""
        print("Initializing audio system...")
        tts = HardwareFactory.create_tts()
        audio = AudioController(tts_engine=tts)

        # Quick status check
        status = audio.check_audio_system()
        print(f"  TTS Available: {status['tts_available']}")
        print(f"  Messages: {status['message_count']}")
        print()

        # Test messages
        print("Playing test messages...")
        test_messages = [
            (AudioMessage.SYSTEM_READY, "System ready"),
            (AudioMessage.RECORDING_START, "Recording started"),
            (AudioMessage.RECORDING_STOP, "Recording complete"),
        ]

        for msg_key, description in test_messages:
            print(f"  - {description}")
            audio.play_message(msg_key)
            audio.wait_until_idle()
            time.sleep(0.3)

        print("  Audio playback complete")
        audio.cleanup()

    def _test_leds(self):
        """Test LED system"""
        print("Initializing LED system...")
        gpio = HardwareFactory.create_gpio()
        led = LEDController(gpio=gpio)

        status = led.get_status()
        print(f"  GPIO Available: {status['gpio_available']}")
        print(f"  Pins: G={status['pins']['green']}, "
              f"O={status['pins']['orange']}, R={status['pins']['red']}")
        print()

        # Test all patterns
        print("Testing LED patterns...")
        patterns = [
            (LEDPattern.READY, "Green (READY)", 1.5),
            (LEDPattern.RECORDING, "Green Blinking (RECORDING)", 2),
            (LEDPattern.PROCESSING, "Orange (PROCESSING)", 1.5),
            (LEDPattern.ERROR, "Red (ERROR)", 1.5),
            (LEDPattern.OFF, "All OFF", 1),
        ]

        for pattern, description, duration in patterns:
            print(f"  - {description}")
            led.set_status(pattern)
            time.sleep(duration)

        print("  LED test complete")
        led.cleanup()

    def _test_button(self):
        """Test button system"""
        print("Initializing button system...")
        gpio = HardwareFactory.create_gpio()
        button = ButtonController(gpio=gpio)

        status = button.get_status()
        print(f"  GPIO Available: {status['gpio_available']}")
        print(f"  Button Pin: GPIO {status['pin']}")
        print()

        # Track presses
        self.button_presses = []

        def on_press(press_type):
            self.button_presses.append(press_type)
            print(f"  - Detected: {press_type} press")

        button.register_callback(on_press)

        print("Button test (10 seconds)...")
        print("  Press button to test (single and double presses)")

        # Check if we're on real hardware
        if status['gpio_available']:
            print("  Waiting for button presses...")
        else:
            print("  Mock mode: press 's' for single, 'd' for double")

        # Wait for button presses
        start_time = time.time()
        while time.time() - start_time < 10:
            time.sleep(0.5)

        print()
        print(f"  Detected {len(self.button_presses)} button presses")

        if len(self.button_presses) == 0:
            print("  WARNING: No button presses detected")
            print("  This is OK if you didn't press the button")

        button.cleanup()

    def _print_summary(self):
        """Print test summary"""
        print("=" * 70)
        print(" " * 25 + "TEST SUMMARY")
        print("=" * 70)
        print()

        print(f"Tests Passed: {len(self.passed_tests)}/{len(self.passed_tests) + len(self.failed_tests)}")
        print()

        if self.passed_tests:
            print("PASSED:")
            for test in self.passed_tests:
                print(f"  - {test}")
            print()

        if self.failed_tests:
            print("FAILED:")
            for test, error in self.failed_tests:
                print(f"  - {test}")
                print(f"    Error: {error}")
            print()

        if not self.failed_tests:
            print("All hardware tests passed!")
            print("System is ready for deployment.")
        else:
            print("Some tests failed. Please investigate before deploying.")

        print()


def main():
    """Main entry point"""
    suite = HardwareTestSuite()

    try:
        success = suite.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nERROR: Test suite crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
