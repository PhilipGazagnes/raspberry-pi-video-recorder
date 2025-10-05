"""
Storage Factory

Factory pattern for creating storage implementations.
Follows the same pattern as hardware/factory.py.
"""

import logging
from typing import Literal, Optional

from storage.config import StorageConfig
from storage.implementations.local_storage import LocalStorage
from storage.implementations.mock_storage import MockStorage
from storage.interfaces.storage_interface import StorageInterface

# Type alias for better type hints
StorageMode = Literal["auto", "real", "mock"]


class StorageFactory:
    """
    Factory for creating storage interface implementations.

    Usage:
        # Auto-detect (uses real storage)
        storage = StorageFactory.create_storage()

        # Force mock mode (useful for testing)
        storage = StorageFactory.create_storage(mode="mock")
    """

    _logger = logging.getLogger(__name__)

    @classmethod
    def create_storage(
        cls,
        mode: StorageMode = "auto",
        config: Optional[StorageConfig] = None,
    ) -> StorageInterface:
        """
        Create a storage interface instance.

        Args:
            mode: "auto" (use real), "real" (force real), "mock" (force simulation)
            config: StorageConfig object (None = create default)

        Returns:
            StorageInterface implementation (LocalStorage or MockStorage)

        Example:
            # Normal usage - real storage
            storage = StorageFactory.create_storage()

            # Testing with mock
            storage = StorageFactory.create_storage(mode="mock")
        """
        if mode == "mock":
            cls._logger.info("Creating Mock Storage (forced)")
            return MockStorage()

        # "auto" or "real" - both use real storage
        # (unlike hardware where auto tries real then falls back to mock,
        # storage is always available so we don't need fallback logic)
        cls._logger.info("Creating Local Storage")
        return LocalStorage(config)

    @classmethod
    def is_storage_available(cls) -> bool:
        """
        Check if storage system is available.

        For local storage, this always returns True unless
        there's a critical filesystem error.

        Returns:
            True if storage is functional
        """
        try:
            storage = LocalStorage()
            available = storage.is_available()
            storage.cleanup()
            return available
        except Exception as e:
            cls._logger.error(f"Storage availability check failed: {e}")
            return False


# Convenience functions for quick creation


def create_storage(
    force_mock: bool = False,
    config: Optional[StorageConfig] = None,
) -> StorageInterface:
    """
    Quick storage creation with simple mock override.

    Args:
        force_mock: If True, always use mock (good for testing)
        config: StorageConfig object

    Returns:
        Storage interface

    Example:
        # Normal usage
        storage = create_storage()

        # Testing
        storage = create_storage(force_mock=True)
    """
    mode = "mock" if force_mock else "auto"
    return StorageFactory.create_storage(mode=mode, config=config)
