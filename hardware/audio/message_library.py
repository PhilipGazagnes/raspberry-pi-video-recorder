"""
Message Library

Manages predefined voice messages for the system.
This is extracted from AudioController following Single Responsibility Principle.

SOLID Principles:
- Single Responsibility: Only manages message storage and retrieval
- Open/Closed: Easy to add new messages without modifying code
"""

import logging
from typing import Dict, List

from hardware.constants import AUDIO_MESSAGE_TEXTS, AudioMessage


class MessageLibrary:
    """
    Library of predefined voice messages.

    This class:
    - Stores message text strings
    - Maps message keys to text
    - Allows custom messages
    - Provides type-safe message retrieval

    Usage:
        lib = MessageLibrary()
        text = lib.get_message(AudioMessage.RECORDING_START)
        lib.add_custom_message("my_custom", "Custom message text")
    """

    def __init__(self):
        """
        Initialize message library with default messages.

        Messages come from constants.py - centralized configuration!
        """
        self.logger = logging.getLogger(__name__)

        # Copy default messages from constants
        # We copy so modifications don't affect the constant
        self._messages = AUDIO_MESSAGE_TEXTS.copy()

        self.logger.info(
            f"Message Library initialized with {len(self._messages)} messages",
        )

    def get_message(self, message_key: AudioMessage) -> str:
        """
        Get message text by key.

        Args:
            message_key: Message identifier from AudioMessage enum

        Returns:
            Message text string

        Raises:
            KeyError: If message key doesn't exist

        Example:
            text = lib.get_message(AudioMessage.RECORDING_START)
            # Returns: "Recording started"
        """
        if message_key not in self._messages:
            raise KeyError(
                f"Unknown message key: {message_key}. "
                f"Available keys: {self.get_available_messages()}",
            )

        return self._messages[message_key]

    def get_message_safe(
        self,
        message_key: AudioMessage,
        default: str = "",
    ) -> str:
        """
        Get message text, returning default if key doesn't exist.

        Safer version of get_message() that never raises exceptions.

        Args:
            message_key: Message identifier
            default: Text to return if key not found

        Returns:
            Message text or default

        Example:
            text = lib.get_message_safe(AudioMessage.RECORDING_START, "Default")
        """
        return self._messages.get(message_key, default)

    def add_custom_message(self, key: AudioMessage, text: str) -> None:
        """
        Add or update a custom message.

        This allows runtime customization of messages without
        modifying constants.py.

        Args:
            key: Message identifier (can be new or existing)
            text: Message text to speak

        Example:
            # Add new message
            lib.add_custom_message(AudioMessage.CUSTOM, "My custom message")

            # Override existing message
            lib.add_custom_message(AudioMessage.SYSTEM_READY, "Système prêt")
        """
        if not text.strip():
            raise ValueError("Message text cannot be empty")

        is_new = key not in self._messages
        self._messages[key] = text

        action = "Added" if is_new else "Updated"
        self.logger.info(f"{action} message '{key.value}': {text}")

    def remove_custom_message(self, key: AudioMessage) -> None:
        """
        Remove a custom message.

        Note: Cannot remove default messages from constants.

        Args:
            key: Message identifier to remove

        Raises:
            KeyError: If message doesn't exist
            ValueError: If trying to remove default message
        """
        if key not in self._messages:
            raise KeyError(f"Message key '{key.value}' not found")

        # Check if this is a default message
        if key in AUDIO_MESSAGE_TEXTS:
            raise ValueError(
                f"Cannot remove default message '{key.value}'. "
                f"Use add_custom_message() to override it instead.",
            )

        del self._messages[key]
        self.logger.info(f"Removed custom message '{key.value}'")

    def get_available_messages(self) -> List[AudioMessage]:
        """
        Get list of all available message keys.

        Returns:
            List of AudioMessage enum values

        Example:
            keys = lib.get_available_messages()
            for key in keys:
                print(f"{key.value}: {lib.get_message(key)}")
        """
        return list(self._messages.keys())

    def get_message_count(self) -> Dict[str, int]:
        """
        Get count of default vs custom messages.

        Returns:
            Dictionary with 'default' and 'custom' counts

        Example:
            counts = lib.get_message_count()
            print(f"Default: {counts['default']}, Custom: {counts['custom']}")
        """
        default_count = sum(1 for key in self._messages if key in AUDIO_MESSAGE_TEXTS)
        custom_count = len(self._messages) - default_count

        return {
            "default": default_count,
            "custom": custom_count,
            "total": len(self._messages),
        }

    def reset_to_defaults(self) -> None:
        """
        Reset all messages to defaults from constants.

        This removes all custom messages and restores originals.

        Example:
            # After adding custom messages
            lib.reset_to_defaults()  # Back to original messages
        """
        self._messages = AUDIO_MESSAGE_TEXTS.copy()
        self.logger.info("Message library reset to defaults")

    def __contains__(self, key: AudioMessage) -> bool:
        """
        Check if message key exists.

        Allows: if AudioMessage.RECORDING_START in lib:

        Args:
            key: Message key to check

        Returns:
            True if message exists
        """
        return key in self._messages

    def __len__(self) -> int:
        """
        Get number of messages.

        Allows: len(lib)

        Returns:
            Number of messages in library
        """
        return len(self._messages)

    def __str__(self) -> str:
        """String representation of library for debugging"""
        counts = self.get_message_count()
        return (
            f"MessageLibrary({counts['total']} messages: "
            f"{counts['default']} default, {counts['custom']} custom)"
        )
