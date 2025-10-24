#!/usr/bin/env python3
"""
YouTube Authentication Setup Script

Run this ONCE to authenticate with YouTube and generate token.json.
After this, the system will automatically refresh tokens as needed.

Usage:
    python setup_youtube_auth.py

Requirements:
    1. client_secret.json from Google Cloud Console
    2. .env file with YOUTUBE_CLIENT_SECRET_PATH and YOUTUBE_TOKEN_PATH
    3. pip install google-auth google-auth-oauthlib google-api-python-client
"""

import logging
import os
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_env_file():
    """Load environment variables from .env file"""
    env_path = ".env"

    if not os.path.exists(env_path):
        logger.error("❌ .env file not found in project root")
        logger.info("Create .env file with:")
        logger.info("  YOUTUBE_CLIENT_SECRET_PATH=/path/to/client_secret.json")
        logger.info("  YOUTUBE_TOKEN_PATH=/path/to/token.json")
        sys.exit(1)

    # Simple .env parser (or use python-dotenv if available)
    try:
        from dotenv import load_dotenv

        load_dotenv()
        logger.info("✅ Loaded environment from .env (using python-dotenv)")
    except ImportError:
        # Manual parsing
        logger.info("Loading environment from .env (manual)")
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


def validate_credentials():
    """Validate client_secret.json exists"""
    # Import settings after .env is loaded
    from config import settings

    client_secret_path = settings.YOUTUBE_CLIENT_SECRET_PATH

    if not client_secret_path:
        logger.error("❌ YOUTUBE_CLIENT_SECRET_PATH not set in .env")
        sys.exit(1)

    if not os.path.exists(client_secret_path):
        logger.error(f"❌ client_secret.json not found: {client_secret_path}")
        logger.info("\nTo get client_secret.json:")
        logger.info("1. Go to: https://console.cloud.google.com/apis/credentials")
        logger.info("2. Create OAuth 2.0 Client ID (Desktop app)")
        logger.info("3. Download JSON file")
        logger.info(f"4. Save to: {client_secret_path}")
        sys.exit(1)

    logger.info(f"✅ Found client_secret.json: {client_secret_path}")
    return client_secret_path


def validate_token_path():
    """Validate token.json path is configured"""
    # Import settings after .env is loaded
    from config import settings

    token_path = settings.YOUTUBE_TOKEN_PATH

    if not token_path:
        logger.error("❌ YOUTUBE_TOKEN_PATH not set in .env")
        sys.exit(1)

    # Create directory if needed
    token_dir = os.path.dirname(token_path)
    if token_dir and not os.path.exists(token_dir):
        os.makedirs(token_dir)
        logger.info(f"✅ Created directory: {token_dir}")

    logger.info(f"✅ Token will be saved to: {token_path}")
    return token_path


def check_dependencies():
    """Check required Python packages are installed"""
    required = [
        "google.auth",
        "google_auth_oauthlib",
        "googleapiclient",
    ]

    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        logger.error(f"❌ Missing required packages: {', '.join(missing)}")
        logger.info("\nInstall with:")
        logger.info(
            "pip install google-auth google-auth-oauthlib google-api-python-client",
        )
        sys.exit(1)

    logger.info("✅ All required packages installed")


def run_authentication(client_secret_path: str, token_path: str):
    """Run OAuth authentication flow"""
    from upload.auth.oauth_manager import run_initial_auth

    logger.info("\n" + "=" * 60)
    logger.info("Starting YouTube Authentication")
    logger.info("=" * 60)
    logger.info("\nSteps:")
    logger.info("1. Browser will open automatically")
    logger.info("2. Log in to your Google/YouTube account")
    logger.info("3. Grant permissions to the app")
    logger.info("4. Token will be saved automatically")
    logger.info(
        "\n⚠️  Make sure to use the SAME Google account that owns the YouTube channel!",
    )
    logger.info("\nPress Enter to continue...")
    input()

    success = run_initial_auth(
        client_secret_path=client_secret_path,
        token_path=token_path,
    )

    if success:
        logger.info("\n" + "=" * 60)
        logger.info("✅ AUTHENTICATION SUCCESSFUL!")
        logger.info("=" * 60)
        logger.info(f"\nToken saved to: {token_path}")
        logger.info("\nYou can now use the upload module:")
        logger.info("  from upload import UploadController")
        logger.info("  controller = UploadController()")
        logger.info(
            "\n⚠️  Keep token.json secret - it grants access to your YouTube account!",
        )
    else:
        logger.error("\n" + "=" * 60)
        logger.error("❌ AUTHENTICATION FAILED")
        logger.error("=" * 60)
        logger.error("\nTroubleshooting:")
        logger.error("1. Check client_secret.json is valid")
        logger.error("2. Ensure OAuth consent screen is configured")
        logger.error("3. Check you're using correct Google account")
        sys.exit(1)


def main():
    """Main setup flow"""
    logger.info("=" * 60)
    logger.info("YouTube Authentication Setup")
    logger.info("=" * 60)

    # Step 1: Load .env
    logger.info("\n[Step 1/5] Loading configuration...")
    load_env_file()

    # Step 2: Check dependencies
    logger.info("\n[Step 2/5] Checking dependencies...")
    check_dependencies()

    # Step 3: Validate client_secret.json
    logger.info("\n[Step 3/5] Validating client_secret.json...")
    client_secret_path = validate_credentials()

    # Step 4: Validate token path
    logger.info("\n[Step 4/5] Validating token path...")
    token_path = validate_token_path()

    # Step 5: Run authentication
    logger.info("\n[Step 5/5] Running authentication flow...")
    run_authentication(client_secret_path, token_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\n❌ Unexpected error: {e}", exc_info=True)
        sys.exit(1)
