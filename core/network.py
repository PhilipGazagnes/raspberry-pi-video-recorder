"""
Network Connectivity Checker

Simple utility to check if internet connection is available.
Uses socket connection to external host for reliability.
"""

import logging
import socket
from typing import Tuple

from config.settings import (
    NETWORK_CHECK_HOST,
    NETWORK_CHECK_PORT,
    NETWORK_CHECK_TIMEOUT,
)


def check_internet_connectivity() -> bool:
    """
    Check if internet connection is available.

    Attempts a socket connection to a reliable external host (Google DNS).
    This indicates whether uploads and SSH access would be possible.

    Returns:
        True if internet is available, False otherwise

    Note:
        - Uses socket.create_connection() for speed and reliability
        - Non-blocking, respects timeout setting
        - Lightweight (~10ms per check when network available)
        - Exceptions are caught and logged silently
    """
    logger = logging.getLogger(__name__)

    try:
        # Create a socket with timeout
        socket.create_connection(
            (NETWORK_CHECK_HOST, NETWORK_CHECK_PORT),
            timeout=NETWORK_CHECK_TIMEOUT,
        )
        return True
    except (socket.timeout, OSError):
        # Network unavailable, timeout, or DNS lookup failed
        return False
    except Exception as e:
        logger.debug(f"Unexpected error in connectivity check: {e}")
        return False


def get_network_status() -> Tuple[bool, str]:
    """
    Get human-readable network status.

    Returns:
        Tuple of (is_connected, status_string)

    Example:
        is_connected, status = get_network_status()
        if is_connected:
            print(f"✓ {status}")  # Output: ✓ Internet available
        else:
            print(f"✗ {status}")  # Output: ✗ No internet connection
    """
    is_connected = check_internet_connectivity()
    status = "Internet available" if is_connected else "No internet connection"
    return is_connected, status
