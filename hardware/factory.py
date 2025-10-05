"""
Hardware Factory

Factory pattern for creating hardware implementations.
Automatically selects real or mock implementations based on availability.

Why use a factory?
1. Single place to decide real vs mock hardware
2. Easy to force mock mode for testing
3. Controllers don't need to know about implementation details
4. Follows "Open/Closed Principle" - easy to add new implementations

This is the "Factory Pattern" - a creational design pattern that provides
an interface for creating objects without specifying their concrete classes.
"""

import logging
from typing import Literal

from hardware.implementations.mock_gpio import MockGPIO
from hardware.implementations.mock_tts import MockTTS
from hardware.implementations.pyttsx3_tts import PyTTSx3Engine
from hardware.implementations.rpi_gpio import RaspberryPiGPIO
from hardware.interfaces.gpio_interface import GPIOInterface
from hardware.interfaces.tts_interface import TTSInterface

# Type aliases for better type hints
HardwareMode = Literal["auto", "real", "mock"]


class HardwareFactory:
    """
    Factory for creating hardware interface implementations.

    Usage:
        # Auto-detect (uses real hardware if available, mock otherwise)
        gpio = HardwareFactory.create_gpio()
        tts = HardwareFactory.create_tts()

        # Force mock mode (useful for testing)
        gpio = HardwareFactory.create_gpio(mode="mock")

        # Force real hardware (raises error if not available)
        gpio = HardwareFactory.create_gpio(mode="real")
    """

    _logger = logging.getLogger(__name__)

    @classmethod
    def create_gpio(
        cls,
        mode: HardwareMode = "auto",
    ) -> GPIOInterface:
        """
        Create a GPIO interface instance.

        Args:
            mode: "auto" (detect), "real" (force real hardware),
                  "mock" (force simulation)

        Returns:
            GPIOInterface implementation (RaspberryPiGPIO or MockGPIO)

        Raises:
            RuntimeError: If mode="real" but hardware not available

        Example:
            # Let factory decide based on availability
            gpio = HardwareFactory.create_gpio()

            # Force mock for testing
            gpio = HardwareFactory.create_gpio(mode="mock")
        """
        if mode == "mock":
            cls._logger.info("Creating Mock GPIO (forced)")
            return MockGPIO()

        if mode == "real":
            try:
                gpio = RaspberryPiGPIO()
                cls._logger.info("Creating Raspberry Pi GPIO (forced)")
                return gpio
            except Exception as e:
                raise RuntimeError(
                    f"Real GPIO requested but not available: {e}",
                ) from e

        # mode == "auto" - try real first, fall back to mock
        try:
            gpio = RaspberryPiGPIO()
            cls._logger.info("Creating Raspberry Pi GPIO (auto-detected)")
            return gpio
        except Exception as e:
            cls._logger.warning(
                f"Real GPIO not available ({e}), using Mock GPIO",
            )
            return MockGPIO()

    @classmethod
    def create_tts(
        cls,
        mode: HardwareMode = "auto",
        simulate_timing: bool = True,
    ) -> TTSInterface:
        """
        Create a TTS interface instance.

        Args:
            mode: "auto" (detect), "real" (force real TTS),
                  "mock" (force simulation)
            simulate_timing: For mock TTS, whether to simulate speech duration.
                           True = realistic timing (good for integration tests)
                           False = instant (good for unit tests)

        Returns:
            TTSInterface implementation (PyTTSx3Engine or MockTTS)

        Raises:
            RuntimeError: If mode="real" but TTS not available

        Example:
            # Auto-detect
            tts = HardwareFactory.create_tts()

            # Mock without timing (fast tests)
            tts = HardwareFactory.create_tts(mode="mock", simulate_timing=False)
        """
        if mode == "mock":
            cls._logger.info(
                f"Creating Mock TTS (forced, timing: {simulate_timing})",
            )
            return MockTTS(simulate_timing=simulate_timing)

        if mode == "real":
            try:
                tts = PyTTSx3Engine()
                cls._logger.info("Creating pyttsx3 TTS (forced)")
                return tts
            except Exception as e:
                raise RuntimeError(
                    f"Real TTS requested but not available: {e}",
                ) from e

        # mode == "auto" - try real first, fall back to mock
        try:
            tts = PyTTSx3Engine()
            cls._logger.info("Creating pyttsx3 TTS (auto-detected)")
            return tts
        except Exception as e:
            cls._logger.warning(
                f"Real TTS not available ({e}), using Mock TTS",
            )
            return MockTTS(simulate_timing=simulate_timing)

    @classmethod
    def is_real_hardware_available(cls) -> dict[str, bool]:
        """
        Check which real hardware is available.

        Useful for diagnostics and configuration display.

        Returns:
            Dictionary with availability status:
            {
                'gpio': True/False,
                'tts': True/False
            }

        Example:
            status = HardwareFactory.is_real_hardware_available()
            if not status['gpio']:
                print("Warning: Running in GPIO simulation mode")
        """
        status = {
            "gpio": False,
            "tts": False,
        }

        # Check GPIO
        try:
            gpio = RaspberryPiGPIO()
            status["gpio"] = gpio.is_available()
            gpio.cleanup()
        except Exception:
            pass

        # Check TTS
        try:
            tts = PyTTSx3Engine()
            status["tts"] = tts.is_available()
            tts.cleanup()
        except Exception:
            pass

        return status


# Convenience functions for quick creation
# These are shortcuts for the most common usage patterns


def create_gpio(force_mock: bool = False) -> GPIOInterface:
    """
    Quick GPIO creation with simple mock override.

    Args:
        force_mock: If True, always use mock (good for testing)

    Returns:
        GPIO interface

    Example:
        # Normal usage
        gpio = create_gpio()

        # Testing
        gpio = create_gpio(force_mock=True)
    """
    mode = "mock" if force_mock else "auto"
    return HardwareFactory.create_gpio(mode=mode)


def create_tts(force_mock: bool = False, fast_mode: bool = False) -> TTSInterface:
    """
    Quick TTS creation with simple options.

    Args:
        force_mock: If True, always use mock
        fast_mode: If True and using mock, skip timing simulation

    Returns:
        TTS interface

    Example:
        # Normal usage
        tts = create_tts()

        # Fast tests
        tts = create_tts(force_mock=True, fast_mode=True)
    """
    mode = "mock" if force_mock else "auto"
    simulate_timing = not fast_mode
    return HardwareFactory.create_tts(mode=mode, simulate_timing=simulate_timing)
