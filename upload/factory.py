"""
Upload Factory

Factory pattern for creating uploader implementations.
Follows same pattern as hardware/factory.py for consistency.

Automatically configures from environment variables.
"""

import logging
import os
from typing import Literal, Optional

from upload.auth.oauth_manager import OAuthManager
from upload.implementations.mock_uploader import MockUploader
from upload.implementations.youtube_uploader import YouTubeUploader
from upload.interfaces.uploader_interface import UploaderInterface

# Type alias
UploaderMode = Literal["auto", "youtube", "mock"]


class UploaderFactory:
    """
    Factory for creating uploader implementations.

    Reads configuration from environment variables:
    - YOUTUBE_CLIENT_SECRET_PATH: Path to client_secret.json
    - YOUTUBE_TOKEN_PATH: Path to token.json
    - YOUTUBE_PLAYLIST_ID: Default playlist ID

    Usage:
        # Auto-detect from environment
        uploader = UploaderFactory.create_uploader()

        # Force mock for testing
        uploader = UploaderFactory.create_uploader(mode="mock")
    """

    _logger = logging.getLogger(__name__)

    @classmethod
    def create_uploader(
        cls,
        mode: UploaderMode = "auto",
        playlist_id: Optional[str] = None,
    ) -> UploaderInterface:
        """
        Create an uploader instance.

        Args:
            mode: "auto" (from env), "youtube" (force real), "mock" (force sim)
            playlist_id: Override playlist ID from environment

        Returns:
            UploaderInterface implementation

        Raises:
            RuntimeError: If mode="youtube" but credentials not available

        Example:
            # Normal usage
            uploader = UploaderFactory.create_uploader()

            # Testing
            uploader = UploaderFactory.create_uploader(mode="mock")
        """
        if mode == "mock":
            cls._logger.info("Creating Mock Uploader (forced)")
            return MockUploader(playlist_id=playlist_id)

        if mode == "youtube":
            try:
                uploader = cls._create_youtube_uploader(playlist_id)
                cls._logger.info("Creating YouTube Uploader (forced)")
                return uploader
            except Exception as e:
                raise RuntimeError(
                    f"YouTube uploader requested but not available: {e}"
                ) from e

        # mode == "auto" - try YouTube first, fall back to mock
        try:
            uploader = cls._create_youtube_uploader(playlist_id)
            cls._logger.info("Creating YouTube Uploader (auto-detected)")
            return uploader
        except Exception as e:
            cls._logger.warning(
                f"YouTube uploader not available ({e}), using Mock Uploader"
            )
            return MockUploader(playlist_id=playlist_id)

    @classmethod
    def _create_youtube_uploader(
        cls,
        playlist_id: Optional[str] = None,
    ) -> YouTubeUploader:
        """
        Create YouTube uploader from environment configuration.

        Reads from .env:
        - YOUTUBE_CLIENT_SECRET_PATH
        - YOUTUBE_TOKEN_PATH
        - YOUTUBE_PLAYLIST_ID (if playlist_id not provided)

        Returns:
            Configured YouTubeUploader

        Raises:
            ValueError: If required env vars missing
            RuntimeError: If OAuth initialization fails
        """
        # Get credentials paths from environment
        client_secret_path = os.getenv("YOUTUBE_CLIENT_SECRET_PATH")
        token_path = os.getenv("YOUTUBE_TOKEN_PATH")

        if not client_secret_path:
            raise ValueError(
                "YOUTUBE_CLIENT_SECRET_PATH not set in environment. "
                "Add to .env file: YOUTUBE_CLIENT_SECRET_PATH=/path/to/client_secret.json"
            )

        if not token_path:
            raise ValueError(
                "YOUTUBE_TOKEN_PATH not set in environment. "
                "Add to .env file: YOUTUBE_TOKEN_PATH=/path/to/token.json"
            )

        # Get playlist ID (argument overrides environment)
        target_playlist = playlist_id or os.getenv("YOUTUBE_PLAYLIST_ID")

        # Create OAuth manager
        oauth_manager = OAuthManager(
            client_secret_path=client_secret_path,
            token_path=token_path,
        )

        # Create uploader
        uploader = YouTubeUploader(
            oauth_manager=oauth_manager,
            playlist_id=target_playlist,
        )

        return uploader

    @classmethod
    def is_youtube_available(cls) -> bool:
        """
        Check if YouTube uploader can be created.

        Returns:
            True if all credentials and libraries available
        """
        try:
            cls._create_youtube_uploader()
            return True
        except Exception:
            return False


# Convenience function for quick creation
def create_uploader(
    force_mock: bool = False,
    playlist_id: Optional[str] = None,
) -> UploaderInterface:
    """
    Quick uploader creation with simple mock override.

    Args:
        force_mock: If True, always use mock
        playlist_id: Override playlist ID from environment

    Returns:
        UploaderInterface

    Example:
        # Normal usage
        uploader = create_uploader()

        # Testing
        uploader = create_uploader(force_mock=True)
    """
    mode = "mock" if force_mock else "auto"
    return UploaderFactory.create_uploader(mode=mode, playlist_id=playlist_id)
