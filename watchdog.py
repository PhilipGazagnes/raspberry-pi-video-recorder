#!/usr/bin/env python3
"""
Watchdog for Recorder Service

Monitors heartbeat and restarts service if frozen.
Implements 3-level recovery: restart → multi-restart → reboot

Recovery Strategy:
1. Level 1: Service restart on stale heartbeat (via systemd)
2. Level 2: Multiple restarts within time window triggers escalation
3. Level 3: System reboot if service unrecoverable

The watchdog runs continuously, checking the heartbeat file written by
recorder_service.py. If the heartbeat becomes stale (older than
HEARTBEAT_TIMEOUT), it triggers a service restart.

If multiple restarts occur within WATCHDOG_RESTART_WINDOW, the watchdog
assumes the service is fundamentally broken and triggers a system reboot
as a last resort.
"""

import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import (
    HEARTBEAT_FILE,
    HEARTBEAT_TIMEOUT,
    LOG_DIR,
    LOG_REBOOT_TRIGGER_FILE,
    LOG_WATCHDOG_FILE,
    WATCHDOG_CHECK_INTERVAL,
    WATCHDOG_MAX_RESTART_ATTEMPTS,
    WATCHDOG_RESTART_WINDOW,
)

# Setup logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s | %(name)s",
    handlers=[
        logging.FileHandler(Path(LOG_DIR) / LOG_WATCHDOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class Watchdog:
    """
    Heartbeat monitor and service recovery manager.

    Monitors the heartbeat file written by recorder_service.py and takes
    action when the service appears frozen or unresponsive.

    Attributes:
        restart_count: Number of restarts in current window
        restart_window_start: Start time of current restart window
    """

    def __init__(self):
        """Initialize watchdog with restart tracking."""
        self.restart_count = 0
        self.restart_window_start = time.time()

    def check_heartbeat(self) -> bool:
        """
        Check if heartbeat is fresh.

        Reads the heartbeat file and verifies the timestamp is recent.
        A stale heartbeat indicates the service may be frozen.

        Returns:
            True if heartbeat is fresh (within HEARTBEAT_TIMEOUT)
            False if heartbeat is stale or file is missing

        Note:
            This method never raises exceptions - all errors are logged
            and treated as failed heartbeat checks.
        """
        try:
            heartbeat_path = Path(HEARTBEAT_FILE)

            if not heartbeat_path.exists():
                logger.warning("Heartbeat file not found")
                return False

            heartbeat = json.loads(heartbeat_path.read_text())
            timestamp = datetime.fromisoformat(heartbeat["timestamp"])
            age = (datetime.now() - timestamp).total_seconds()

            if age > HEARTBEAT_TIMEOUT:
                logger.error(
                    f"Heartbeat stale! Age: {age:.1f}s, "
                    f"Last state: {heartbeat.get('state', 'unknown')}",
                )
                return False

            logger.debug(f"Heartbeat OK (age: {age:.1f}s)")
            return True

        except Exception as e:
            logger.error(f"Failed to read heartbeat: {e}")
            return False

    def restart_service(self):
        """
        Restart recorder service via systemd.

        Increments restart counter and triggers a service restart.
        If restart counter exceeds MAX_RESTART_ATTEMPTS within the
        restart window, escalates to system reboot.

        The restart window resets after WATCHDOG_RESTART_WINDOW seconds,
        allowing the counter to reset if the service becomes stable.
        """
        # Reset restart counter if window expired
        if time.time() - self.restart_window_start > WATCHDOG_RESTART_WINDOW:
            self.restart_count = 0
            self.restart_window_start = time.time()

        self.restart_count += 1
        logger.warning(
            f"Restarting service (attempt {self.restart_count}/"
            f"{WATCHDOG_MAX_RESTART_ATTEMPTS})",
        )

        try:
            subprocess.run(
                ["sudo", "systemctl", "restart", "recorder.service"],
                check=True,
                timeout=30,
            )
            logger.info("Service restarted successfully")

            # Wait for service to start
            time.sleep(10)

        except subprocess.TimeoutExpired:
            logger.error("Service restart timed out!")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart service: {e}")

    def trigger_reboot(self):
        """
        Trigger system reboot (last resort).

        Called when the service has failed to recover after multiple
        restart attempts. Logs the reboot trigger to a separate file
        for post-mortem analysis.

        This is the nuclear option - only called when all other recovery
        attempts have failed and the service is fundamentally broken.
        """
        logger.critical(
            f"Service restart failed {WATCHDOG_MAX_RESTART_ATTEMPTS} times. "
            "Triggering system reboot...",
        )

        try:
            # Log to separate file for post-mortem analysis
            reboot_log = Path(LOG_DIR) / LOG_REBOOT_TRIGGER_FILE
            reboot_log.write_text(
                f"{datetime.now().isoformat()}\n"
                f"Reason: Service unrecoverable after "
                f"{WATCHDOG_MAX_RESTART_ATTEMPTS} restarts\n",
            )

            subprocess.run(["sudo", "reboot"], check=True, timeout=10)

        except Exception as e:
            logger.critical(f"Failed to trigger reboot: {e}")

    def run(self):
        """
        Main watchdog loop.

        Runs continuously, checking heartbeat at regular intervals.
        Takes recovery action when heartbeat becomes stale.

        The loop runs until:
        - Keyboard interrupt (Ctrl+C)
        - System reboot triggered
        - Fatal error

        Recovery flow:
        1. Check heartbeat
        2. If stale → restart service
        3. Wait and verify restart worked
        4. If still stale and max restarts reached → reboot system
        5. Otherwise, continue monitoring
        """
        logger.info("Watchdog started")
        logger.info(f"Monitoring heartbeat: {HEARTBEAT_FILE}")
        logger.info(f"Heartbeat timeout: {HEARTBEAT_TIMEOUT}s")
        logger.info(f"Check interval: {WATCHDOG_CHECK_INTERVAL}s")
        logger.info(
            f"Max restart attempts: {WATCHDOG_MAX_RESTART_ATTEMPTS} "
            f"in {WATCHDOG_RESTART_WINDOW}s window",
        )

        while True:
            try:
                if not self.check_heartbeat():
                    self.restart_service()

                    # Check if restart worked
                    time.sleep(15)
                    if not self.check_heartbeat():
                        if self.restart_count >= WATCHDOG_MAX_RESTART_ATTEMPTS:
                            self.trigger_reboot()
                            break

                time.sleep(WATCHDOG_CHECK_INTERVAL)

            except KeyboardInterrupt:
                logger.info("Watchdog stopped by user")
                break
            except Exception as e:
                logger.error(f"Watchdog error: {e}", exc_info=True)
                time.sleep(WATCHDOG_CHECK_INTERVAL)


if __name__ == "__main__":
    watchdog = Watchdog()
    watchdog.run()
