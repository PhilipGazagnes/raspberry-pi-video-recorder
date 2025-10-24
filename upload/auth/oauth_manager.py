"""
OAuth Manager

Handles Google OAuth 2.0 authentication for YouTube API.
Uses refresh token for automated, long-lived authentication.

Flow:
1. Initial setup: Run setup_youtube_auth.py once to generate token.json
2. Runtime: This class uses token.json for automatic authentication
3. Token refresh: Happens automatically when needed (transparent to user)
"""

import logging
import os
from typing import Optional

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

from upload.constants import YOUTUBE_SCOPES


class OAuthManager:
    """
    Manages Google OAuth 2.0 authentication.

    This class:
    - Loads credentials from token.json
    - Refreshes expired tokens automatically
    - Validates authentication status
    """

    def __init__(
        self,
        client_secret_path: str,
        token_path: str,
    ):
        """
        Initialize OAuth manager.

        Args:
            client_secret_path: Path to client_secret.json from Google Cloud
            token_path: Path to token.json (created during initial auth)

        Example:
            oauth = OAuthManager(
                client_secret_path="credentials/client_secret.json",
                token_path="credentials/token.json"
            )
        """
        self.logger = logging.getLogger(__name__)

        if not GOOGLE_AUTH_AVAILABLE:
            raise ImportError(
                "Google auth libraries not available. "
                "Install with: pip install google-auth google-auth-oauthlib "
                "google-auth-httplib2 google-api-python-client",
            )

        self.client_secret_path = client_secret_path
        self.token_path = token_path
        self.credentials: Optional[Credentials] = None

        # Validate paths
        self._validate_paths()

        # Load credentials
        self._load_credentials()

        self.logger.info("OAuth Manager initialized")

    def _validate_paths(self) -> None:
        """
        Validate that required credential files exist.

        Raises:
            FileNotFoundError: If client_secret.json doesn't exist
            RuntimeError: If token.json doesn't exist (needs initial setup)
        """
        if not os.path.exists(self.client_secret_path):
            raise FileNotFoundError(
                f"Client secret file not found: {self.client_secret_path}\n"
                f"Download from Google Cloud Console > Credentials",
            )

        if not os.path.exists(self.token_path):
            raise RuntimeError(
                f"Token file not found: {self.token_path}\n"
                f"Run 'python setup_youtube_auth.py' first to authenticate",
            )

    def _load_credentials(self) -> None:
        """
        Load credentials from token.json.

        If token is expired but has refresh token, automatically refreshes.
        """
        try:
            self.credentials = Credentials.from_authorized_user_file(
                self.token_path,
                YOUTUBE_SCOPES,
            )

            # Check if credentials are valid
            if not self.credentials or not self.credentials.valid:
                if (
                    self.credentials
                    and self.credentials.expired
                    and self.credentials.refresh_token
                ):
                    # Token expired but can be refreshed
                    self.logger.info("Access token expired, refreshing...")
                    self.credentials.refresh(Request())
                    self._save_credentials()
                    self.logger.info("Access token refreshed successfully")
                else:
                    # No refresh token - need to re-authenticate
                    raise RuntimeError(
                        "Credentials invalid and cannot be refreshed. "
                        "Run 'python setup_youtube_auth.py' to re-authenticate",
                    )

            self.logger.debug("Credentials loaded and validated")

        except Exception as e:
            self.logger.error(f"Failed to load credentials: {e}")
            raise

    def _save_credentials(self) -> None:
        """Save refreshed credentials back to token.json"""
        try:
            with open(self.token_path, "w") as token_file:
                token_file.write(self.credentials.to_json())
            self.logger.debug("Credentials saved to token file")
        except Exception as e:
            self.logger.warning(f"Failed to save credentials: {e}")

    def get_credentials(self) -> Credentials:
        """
        Get valid OAuth credentials.

        Automatically refreshes if expired.

        Returns:
            Valid Google OAuth credentials

        Raises:
            RuntimeError: If credentials cannot be obtained
        """
        # Check if refresh needed
        if (
            self.credentials
            and self.credentials.expired
            and self.credentials.refresh_token
        ):
            self.logger.debug("Token expired, refreshing...")
            self.credentials.refresh(Request())
            self._save_credentials()

        if not self.credentials or not self.credentials.valid:
            raise RuntimeError(
                "Cannot get valid credentials. "
                "Run 'python setup_youtube_auth.py' to re-authenticate",
            )

        return self.credentials

    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated with valid credentials.

        Returns:
            True if credentials are valid
        """
        try:
            creds = self.get_credentials()
            return creds is not None and creds.valid
        except Exception:
            return False

    def revoke_credentials(self) -> bool:
        """
        Revoke current credentials.

        This logs out the application. User will need to re-authenticate.

        Returns:
            True if successfully revoked
        """
        try:
            if self.credentials:
                # Revoke token on Google's servers
                self.credentials.revoke(Request())

            # Delete local token file
            if os.path.exists(self.token_path):
                os.remove(self.token_path)

            self.credentials = None
            self.logger.info("Credentials revoked")
            return True

        except Exception as e:
            self.logger.error(f"Failed to revoke credentials: {e}")
            return False


def run_initial_auth(
    client_secret_path: str,
    token_path: str,
    port: int = 8080,
) -> bool:
    """
    Run initial OAuth authentication flow.

    This is a standalone function for the setup script.
    Opens browser for user to grant permissions.

    Args:
        client_secret_path: Path to client_secret.json
        token_path: Where to save token.json
        port: Local port for OAuth callback (default: 8080)

    Returns:
        True if authentication successful

    Example:
        run_initial_auth(
            "credentials/client_secret.json",
            "credentials/token.json"
        )
    """
    logger = logging.getLogger(__name__)

    if not GOOGLE_AUTH_AVAILABLE:
        logger.error("Google auth libraries not installed")
        return False

    try:
        # Create flow from client secrets
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secret_path,
            YOUTUBE_SCOPES,
        )

        # Run local server for OAuth callback
        logger.info(f"Starting OAuth flow on port {port}...")
        logger.info("A browser window will open for authentication")

        credentials = flow.run_local_server(port=port)

        # Save credentials
        with open(token_path, "w") as token_file:
            token_file.write(credentials.to_json())

        logger.info(f"✅ Authentication successful! Token saved to: {token_path}")
        return True

    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return False
