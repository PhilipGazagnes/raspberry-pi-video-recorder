"""
Mock GPIO Implementation

Simulated GPIO for development and testing without Raspberry Pi hardware.
Allows you to develop and test on your laptop, CI/CD servers, etc.

This is a "Test Double" (specifically, a "Fake" - it has working logic but no real hardware).

Why mock hardware?
1. Development: Write code on Mac/PC before deploying to Pi
2. Testing: Fast unit tests without hardware
3. CI/CD: Automated tests in GitHub Actions
4. Debugging: Easier to trace logic without timing issues
"""

import logging
import threading
import time
from typing import Callable, Optional

from hardware.interfaces.gpio_interface import (
    EdgeDetection,
    GPIOError,
    GPIOInterface,
    PinState,
    PullMode,
)


class MockGPIO(GPIOInterface):
    """
    Simulated GPIO that mimics Raspberry Pi behavior.

    This maintains state for each pin and simulates edge detection callbacks.
    Perfect for testing button/LED logic without hardware.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Track pin configurations and states
        # Key: pin number, Value: dict with pin info
        self._pins: dict[int, dict] = {}

        # Track event callbacks
        # Key: pin number, Value: callback info
        self._callbacks: dict[int, dict] = {}

        self.logger.info("Mock GPIO initialized (simulation mode)")

    def setup_output(self, pin: int) -> None:
        """Configure pin as output"""
        self._pins[pin] = {
            'mode': 'output',
            'state': PinState.LOW,  # Start low
        }
        self.logger.debug(f"[MOCK] Pin {pin} configured as OUTPUT")

    def setup_input(
        self,
        pin: int,
        pull_mode: PullMode = PullMode.UP
    ) -> None:
        """Configure pin as input"""
        # With pull-up, pin starts HIGH (pulled to 3.3V)
        # With pull-down, pin starts LOW (pulled to 0V)
        initial_state = PinState.HIGH if pull_mode == PullMode.UP else PinState.LOW

        self._pins[pin] = {
            'mode': 'input',
            'state': initial_state,
            'pull': pull_mode,
        }
        self.logger.debug(
            f"[MOCK] Pin {pin} configured as INPUT "
            f"(pull: {pull_mode.value}, initial: {initial_state.name})"
        )

    def write(self, pin: int, state: PinState) -> None:
        """Set output pin state"""
        if pin not in self._pins:
            raise GPIOError(f"Pin {pin} not configured")

        if self._pins[pin]['mode'] != 'output':
            raise GPIOError(f"Pin {pin} not configured as output")

        old_state = self._pins[pin]['state']
        self._pins[pin]['state'] = state

        # Log state changes for debugging
        if old_state != state:
            self.logger.debug(f"[MOCK] Pin {pin}: {old_state.name} -> {state.name}")

    def read(self, pin: int) -> PinState:
        """Read input pin state"""
        if pin not in self._pins:
            raise GPIOError(f"Pin {pin} not configured")

        return self._pins[pin]['state']

    def add_event_callback(
        self,
        pin: int,
        edge: EdgeDetection,
        callback: Callable[[int], None],
        debounce_ms: int = 0
    ) -> None:
        """Register callback for pin state changes"""
        if pin not in self._pins:
            raise GPIOError(f"Pin {pin} not configured")

        if self._pins[pin]['mode'] != 'input':
            raise GPIOError(f"Pin {pin} not configured as input")

        self._callbacks[pin] = {
            'edge': edge,
            'callback': callback,
            'debounce_ms': debounce_ms,
            'last_trigger': 0,  # Timestamp of last trigger (for debouncing)
        }

        self.logger.debug(
            f"[MOCK] Event callback added to pin {pin} "
            f"(edge: {edge.value}, debounce: {debounce_ms}ms)"
        )

    def remove_event_callback(self, pin: int) -> None:
        """Remove event callback"""
        if pin in self._callbacks:
            del self._callbacks[pin]
            self.logger.debug(f"[MOCK] Event callback removed from pin {pin}")

    def cleanup(self, pins: Optional[list[int]] = None) -> None:
        """Reset pins to safe state"""
        if pins is None:
            pins_to_clean = list(self._pins.keys())
        else:
            pins_to_clean = pins

        for pin in pins_to_clean:
            if pin in self._pins:
                del self._pins[pin]
            if pin in self._callbacks:
                del self._callbacks[pin]

        self.logger.info(f"[MOCK] Cleaned up pins: {pins_to_clean}")

    def is_available(self) -> bool:
        """Mock GPIO is always "available" (it's simulated)"""
        return True

    # =========================================================================
    # TESTING HELPER METHODS (not part of GPIOInterface)
    # =========================================================================
    # These methods are ONLY for testing - they simulate hardware events

    def simulate_button_press(self, pin: int) -> None:
        """
        Simulate a button press on the given pin.
        Useful for testing button controller logic.

        This simulates the electrical signal from a real button press:
        - With pull-up resistor: HIGH -> LOW -> HIGH
        - With pull-down resistor: LOW -> HIGH -> LOW
        """
        if pin not in self._pins or self._pins[pin]['mode'] != 'input':
            raise GPIOError(f"Pin {pin} not configured as input")

        pull_mode = self._pins[pin]['pull']
        is_pull_up = pull_mode == PullMode.UP

        # Simulate press (state change)
        press_state = PinState.LOW if is_pull_up else PinState.HIGH
        self._trigger_edge_event(pin, press_state)

        self.logger.info(f"[MOCK] Simulated button PRESS on pin {pin}")

        # Simulate button held for 100ms
        time.sleep(0.1)

        # Simulate release (return to resting state)
        release_state = PinState.HIGH if is_pull_up else PinState.LOW
        self._trigger_edge_event(pin, release_state)

        self.logger.info(f"[MOCK] Simulated button RELEASE on pin {pin}")

    def simulate_double_press(self, pin: int, delay_ms: int = 200) -> None:
        """
        Simulate a double button press (two presses in quick succession).

        Args:
            pin: Input pin number
            delay_ms: Time between first and second press (milliseconds)
        """
        self.simulate_button_press(pin)
        time.sleep(delay_ms / 1000.0)
        self.simulate_button_press(pin)
        self.logger.info(f"[MOCK] Simulated DOUBLE press on pin {pin}")

    def _trigger_edge_event(self, pin: int, new_state: PinState) -> None:
        """
        Internal method to trigger edge detection callback.

        This mimics how RPi.GPIO fires callbacks on state changes.
        """
        if pin not in self._callbacks:
            return  # No callback registered

        old_state = self._pins[pin]['state']

        # Update pin state
        self._pins[pin]['state'] = new_state

        callback_info = self._callbacks[pin]
        edge = callback_info['edge']

        # Check if this edge type should trigger
        should_trigger = False

        if edge == EdgeDetection.RISING and old_state == PinState.LOW and new_state == PinState.HIGH:
            should_trigger = True
        elif edge == EdgeDetection.FALLING and old_state == PinState.HIGH and new_state == PinState.LOW:
            should_trigger = True
        elif edge == EdgeDetection.BOTH and old_state != new_state:
            should_trigger = True

        if not should_trigger:
            return

        # Apply debouncing (ignore if too soon after last trigger)
        current_time = time.time()
        debounce_seconds = callback_info['debounce_ms'] / 1000.0

        if current_time - callback_info['last_trigger'] < debounce_seconds:
            self.logger.debug(f"[MOCK] Pin {pin} edge ignored (debounce)")
            return

        callback_info['last_trigger'] = current_time

        # Trigger callback in a separate thread (mimics RPi.GPIO behavior)
        callback = callback_info['callback']
        thread = threading.Thread(
            target=callback,
            args=(pin,),
            daemon=True
        )
        thread.start()

        self.logger.debug(f"[MOCK] Pin {pin} edge triggered: {old_state.name} -> {new_state.name}")

    def get_pin_state(self, pin: int) -> PinState:
        """
        Helper for tests to check current pin state.

        Returns:
            Current state of the pin
        """
        if pin not in self._pins:
            raise GPIOError(f"Pin {pin} not configured")
        return self._pins[pin]['state']

    def get_pin_info(self, pin: int) -> dict:
        """
        Get detailed pin information for debugging.

        Returns:
            Dictionary with pin configuration and state
        """
        if pin not in self._pins:
            raise GPIOError(f"Pin {pin} not configured")

        info = self._pins[pin].copy()
        if pin in self._callbacks:
            info['has_callback'] = True
            info['callback_edge'] = self._callbacks[pin]['edge'].value
        else:
            info['has_callback'] = False

        return info
