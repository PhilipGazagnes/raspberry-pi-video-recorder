"""
Raspberry Pi GPIO Implementation

Concrete implementation of GPIOInterface for Raspberry Pi hardware using
RPi.GPIO library. This wraps the RPi.GPIO library to match our interface.

Why wrap an existing library?
1. Decoupling: If RPi.GPIO changes, only this file needs updating
2. Simplification: Hide RPi.GPIO's complexity behind clean interface
3. Testing: Can swap this for MockGPIO in tests
4. Portability: Easy to add other GPIO libraries (pigpio, gpiozero, etc.)
"""

import logging
from typing import Callable, Optional

try:
    from RPi import GPIO

    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

from hardware.interfaces.gpio_interface import (
    EdgeDetection,
    GPIOError,
    GPIOInterface,
    PinState,
    PullMode,
)


class RaspberryPiGPIO(GPIOInterface):
    """
    Raspberry Pi GPIO implementation using RPi.GPIO library.

    This class translates our clean interface into RPi.GPIO's specific API.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Track which pins we've configured (for cleanup)
        self._configured_pins: set[int] = set()

        if not GPIO_AVAILABLE:
            raise GPIOError(
                "RPi.GPIO library not available. Install with: pip install RPi.GPIO",
            )

        # Set GPIO mode to BCM (Broadcom chip numbering)
        # BCM uses GPIO numbers (GPIO18) vs BOARD uses physical pin numbers (pin 12)
        # BCM is more common in documentation
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)  # Disable warnings about pins already in use
            self.logger.info("Raspberry Pi GPIO initialized (BCM mode)")
        except Exception as e:
            raise GPIOError(f"Failed to initialize GPIO: {e}") from e

    def setup_output(self, pin: int) -> None:
        """Configure pin as output (for LEDs)"""
        try:
            GPIO.setup(pin, GPIO.OUT)
            self._configured_pins.add(pin)
            self.logger.debug(f"Pin {pin} configured as OUTPUT")
        except Exception as e:
            raise GPIOError(f"Failed to setup pin {pin} as output: {e}") from e

    def setup_input(
        self,
        pin: int,
        pull_mode: PullMode = PullMode.UP,
    ) -> None:
        """Configure pin as input (for button)"""
        try:
            # Map our PullMode enum to RPi.GPIO constants
            pull_mapping = {
                PullMode.UP: GPIO.PUD_UP,
                PullMode.DOWN: GPIO.PUD_DOWN,
                PullMode.NONE: GPIO.PUD_OFF,
            }

            gpio_pull = pull_mapping[pull_mode]
            GPIO.setup(pin, GPIO.IN, pull_up_down=gpio_pull)
            self._configured_pins.add(pin)
            self.logger.debug(
                f"Pin {pin} configured as INPUT (pull: {pull_mode.value})",
            )
        except Exception as e:
            raise GPIOError(f"Failed to setup pin {pin} as input: {e}") from e

    def write(self, pin: int, state: PinState) -> None:
        """Set output pin HIGH or LOW"""
        try:
            # Map our PinState enum to RPi.GPIO constants
            gpio_state = GPIO.HIGH if state == PinState.HIGH else GPIO.LOW
            GPIO.output(pin, gpio_state)
            # Don't log every write - too verbose for blinking LEDs
        except Exception as e:
            raise GPIOError(f"Failed to write to pin {pin}: {e}") from e

    def read(self, pin: int) -> PinState:
        """Read input pin state"""
        try:
            value = GPIO.input(pin)
            return PinState.HIGH if value else PinState.LOW
        except Exception as e:
            raise GPIOError(f"Failed to read pin {pin}: {e}") from e

    def add_event_callback(
        self,
        pin: int,
        edge: EdgeDetection,
        callback: Callable[[int], None],
        debounce_ms: int = 0,
    ) -> None:
        """
        Register interrupt callback for pin state changes.

        RPi.GPIO's event detection is interrupt-based - very efficient!
        The callback runs in a separate thread automatically.
        """
        try:
            # Map our EdgeDetection enum to RPi.GPIO constants
            edge_mapping = {
                EdgeDetection.RISING: GPIO.RISING,
                EdgeDetection.FALLING: GPIO.FALLING,
                EdgeDetection.BOTH: GPIO.BOTH,
            }

            gpio_edge = edge_mapping[edge]

            # RPi.GPIO expects bouncetime in milliseconds
            GPIO.add_event_detect(
                pin,
                gpio_edge,
                callback=callback,
                bouncetime=debounce_ms,
            )

            self.logger.debug(
                f"Event callback added to pin {pin} "
                f"(edge: {edge.value}, debounce: {debounce_ms}ms)",
            )
        except Exception as e:
            raise GPIOError(f"Failed to add event callback to pin {pin}: {e}") from e

    def remove_event_callback(self, pin: int) -> None:
        """Remove event callback from pin"""
        try:
            GPIO.remove_event_detect(pin)
            self.logger.debug(f"Event callback removed from pin {pin}")
        except Exception as e:
            # Don't raise - cleanup should be forgiving
            self.logger.warning(f"Failed to remove event callback from pin {pin}: {e}")

    def cleanup(self, pins: Optional[list[int]] = None) -> None:
        """
        Reset GPIO pins and release resources.

        Important: Always call this before program exits to leave pins in safe state.
        """
        try:
            if pins is None:
                # Clean up all pins we configured
                if self._configured_pins:
                    GPIO.cleanup(list(self._configured_pins))
                    self.logger.info(
                        f"Cleaned up {len(self._configured_pins)} GPIO pins",
                    )
                    self._configured_pins.clear()
            else:
                # Clean up specific pins
                GPIO.cleanup(pins)
                self._configured_pins.difference_update(pins)
                self.logger.info(f"Cleaned up GPIO pins: {pins}")
        except Exception as e:
            # Don't raise during cleanup - just log
            self.logger.error(f"Error during GPIO cleanup: {e}")

    def is_available(self) -> bool:
        """Check if running on real Raspberry Pi hardware"""
        return GPIO_AVAILABLE

    def __del__(self):
        """Destructor - ensure cleanup even if not explicitly called"""
        self.cleanup()
