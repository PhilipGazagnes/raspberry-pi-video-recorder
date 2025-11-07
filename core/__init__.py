"""
Core utilities and modules.

Public API:
    - check_internet_connectivity: Check if internet is available
    - get_network_status: Get human-readable network status

Usage:
    from core.network import check_internet_connectivity

    if check_internet_connectivity():
        print("Internet available")
"""

from core.network import check_internet_connectivity, get_network_status

__all__ = [
    "check_internet_connectivity",
    "get_network_status",
]
