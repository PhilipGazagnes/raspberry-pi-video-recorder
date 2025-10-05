"""
GPIO Interface - Abstract Hardware Layer

This defines the contract (interface) that any GPIO implementation must follow.
This is the "Dependency Inversion Principle" from SOLID - depend on abstractions,
not concrete implementations.

Why use an abstract interface?
1. Testability: Can swap real GPIO with mock for tests
2. Flexibility: Easy to support different hardware (RPi, Arduino, etc.)
3. Simulation: Can run on non-Raspberry Pi machines
4. Type safety: mypy can check you're using GPIO correctly

Think of this as a "promise" - any GPIO implementation must provide these methods.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable, Optional


class PinMode(Enum):
    """How a GPIO pin is configured"""

    INPUT = "input"  # Read signals (button)
    OUTPUT = "output"  # Send signals (LED)


class PullMode(Enum):
    """Pull resistor configuration for input pins"""

    UP = "up"  # Pull to HIGH (3.3V) - button press reads LOW
    DOWN = "down"  # Pull to LOW (0V) - button press reads HIGH
    NONE = "none"  # No pull resistor (external resistor required)


class EdgeDetection(Enum):
    """When to trigger interrupt callbacks"""

    RISING = "rising"  # LOW -> HIGH transition
    FALLING = "falling"  # HIGH -> LOW transition
    BOTH = "both"  # Any transition


class PinState(Enum):
    """Digital pin states"""

    LOW = 0  # 0V / False
    HIGH = 1  # 3.3V / True


class GPIOInterface(ABC):
    """
    Abstract base class for GPIO operations.

    Any class that inherits from this MUST implement all @abstractmethod methods.
    This ensures all GPIO implementations have the same interface.

    ABC = Abstract Base Class (from Python's abc module)
    """

    @abstractmethod
    def setup_output(self, pin: int) -> None:
        """
        Configure a pin as an output (for controlling LEDs).

        Args:
            pin: GPIO pin number (BCM numbering)

        Raises:
            GPIOError: If pin setup fails
        """

    @abstractmethod
    def setup_input(
        self,
        pin: int,
        pull_mode: PullMode = PullMode.UP,
    ) -> None:
        """
        Configure a pin as an input (for reading button).

        Args:
            pin: GPIO pin number (BCM numbering)
            pull_mode: Internal pull resistor configuration

        Raises:
            GPIOError: If pin setup fails
        """

    @abstractmethod
    def write(self, pin: int, state: PinState) -> None:
        """
        Set an output pin to HIGH or LOW.

        Args:
            pin: GPIO pin number
            state: Desired pin state (HIGH/LOW)

        Raises:
            GPIOError: If pin isn't configured as output
        """

    @abstractmethod
    def read(self, pin: int) -> PinState:
        """
        Read the current state of an input pin.

        Args:
            pin: GPIO pin number

        Returns:
            Current pin state (HIGH/LOW)

        Raises:
            GPIOError: If pin isn't configured as input
        """

    @abstractmethod
    def add_event_callback(
        self,
        pin: int,
        edge: EdgeDetection,
        callback: Callable[[int], None],
        debounce_ms: int = 0,
    ) -> None:
        """
        Register a callback function to be called when pin changes state.
        This is for interrupt-driven button handling (efficient - no polling).

        Args:
            pin: GPIO pin number
            edge: When to trigger (RISING/FALLING/BOTH)
            callback: Function to call, receives pin number as argument
            debounce_ms: Hardware debounce time in milliseconds

        Raises:
            GPIOError: If pin isn't configured as input
        """

    @abstractmethod
    def remove_event_callback(self, pin: int) -> None:
        """
        Remove event callback from a pin.

        Args:
            pin: GPIO pin number
        """

    @abstractmethod
    def cleanup(self, pins: Optional[list[int]] = None) -> None:
        """
        Reset GPIO pins to safe state and release resources.
        Important to call this before program exits!

        Args:
            pins: Specific pins to cleanup, or None for all pins
        """

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if GPIO hardware is actually available.

        Returns:
            True if running on real hardware, False if simulated
        """


class GPIOError(Exception):
    """
    Custom exception for GPIO-related errors.

    Why custom exceptions?
    - Clear error type (you know it's hardware-related)
    - Can catch specifically: except GPIOError
    - Can add custom error information
    """
