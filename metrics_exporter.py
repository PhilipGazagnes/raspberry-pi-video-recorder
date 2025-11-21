#!/usr/bin/env python3
"""
Metrics Exporter for Recorder Service

Exposes Prometheus-compatible metrics on HTTP endpoint.
Reads from heartbeat file and storage database to provide
comprehensive system monitoring.

Metrics Exposed:
- recorder_up: Service liveness (1=up, 0=down)
- recorder_heartbeat_age_seconds: Age of last heartbeat
- recorder_state: Current system state (booting/ready/recording/etc)
- recorder_recording_active: Whether currently recording
- recorder_upload_queue_size: Videos waiting to upload
- recorder_uptime_seconds: Service uptime
- recorder_disk_free_bytes: Free disk space
- recorder_disk_usage_ratio: Disk usage (0-1)
- recorder_videos_total: Video count by status
- recorder_upload_success_rate: Upload success rate (0-1)

Usage:
    python metrics_exporter.py
    # Metrics available at http://localhost:9101/metrics
"""

import json
import logging
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import HEARTBEAT_FILE, HEARTBEAT_TIMEOUT, METRICS_PORT
from storage import StorageController

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s - %(message)s | %(name)s",
)
logger = logging.getLogger(__name__)


class MetricsExporter:
    """
    Prometheus metrics exporter for recorder service.

    Reads heartbeat file and queries storage database to generate
    metrics in Prometheus text format.

    Attributes:
        storage: StorageController for accessing video metadata
        last_heartbeat: Most recent heartbeat data (if available)
        heartbeat_age: Age of heartbeat in seconds
    """

    def __init__(self):
        """Initialize exporter with storage controller."""
        self.storage = StorageController()
        self.last_heartbeat: Optional[dict] = None
        self.heartbeat_age = 999  # Default to high age (service down)

    def update_metrics(self):
        """
        Update metrics from heartbeat and database.

        Reads the heartbeat file and calculates age.
        Never raises exceptions - errors result in default values
        indicating service is down.
        """
        try:
            # Read heartbeat file
            heartbeat_path = Path(HEARTBEAT_FILE)
            if heartbeat_path.exists():
                self.last_heartbeat = json.loads(heartbeat_path.read_text())
                timestamp = datetime.fromisoformat(
                    self.last_heartbeat["timestamp"],
                )
                self.heartbeat_age = (datetime.now() - timestamp).total_seconds()
            else:
                self.heartbeat_age = 999

        except Exception as e:
            logger.error(f"Failed to read heartbeat: {e}")
            self.heartbeat_age = 999

    def generate_metrics(self) -> str:  # noqa: PLR0915
        """
        Generate Prometheus metrics in text format.

        Returns metrics for:
        - Service liveness and heartbeat age
        - Current state and recording status
        - Upload queue depth and uptime
        - Disk space and usage
        - Video counts by status
        - Upload success rate

        Returns:
            Prometheus text format metrics (newline-separated)

        Prometheus Text Format:
            # HELP metric_name Description
            # TYPE metric_name gauge|counter
            metric_name{label="value"} 123.45

        Example:
            # HELP recorder_up Whether recorder service is responding
            # TYPE recorder_up gauge
            recorder_up 1
        """
        self.update_metrics()

        metrics = []

        # Heartbeat metrics - indicates if service is alive
        metrics.append(
            "# HELP recorder_up Whether recorder service is responding",
        )
        metrics.append("# TYPE recorder_up gauge")
        is_up = 1 if self.heartbeat_age < HEARTBEAT_TIMEOUT else 0
        metrics.append(f"recorder_up {is_up}")

        metrics.append(
            "# HELP recorder_heartbeat_age_seconds Age of last heartbeat",
        )
        metrics.append("# TYPE recorder_heartbeat_age_seconds gauge")
        metrics.append(f"recorder_heartbeat_age_seconds {self.heartbeat_age:.1f}")

        if self.last_heartbeat:
            # State metrics - one-hot encoding for current state
            # Only one state will be 1, others will be 0
            state = self.last_heartbeat.get("state", "unknown")
            metrics.append(
                "# HELP recorder_state Current system state (one-hot encoded)",
            )
            metrics.append("# TYPE recorder_state gauge")
            metrics.extend(
                f'recorder_state{{state="{s}"}} {1 if state == s else 0}'
                for s in ["booting", "ready", "recording", "processing", "error"]
            )

            # Recording metrics - whether actively recording
            metrics.append(
                "# HELP recorder_recording_active Whether currently recording",
            )
            metrics.append("# TYPE recorder_recording_active gauge")
            recording = 1 if self.last_heartbeat.get("recording_active") else 0
            metrics.append(f"recorder_recording_active {recording}")

            # Upload queue metrics - how many videos waiting to upload
            metrics.append("# HELP recorder_upload_queue_size Upload queue depth")
            metrics.append("# TYPE recorder_upload_queue_size gauge")
            queue_size = self.last_heartbeat.get("upload_queue_size", 0)
            metrics.append(f"recorder_upload_queue_size {queue_size}")

            # Uptime - how long service has been running
            metrics.append("# HELP recorder_uptime_seconds Service uptime")
            metrics.append("# TYPE recorder_uptime_seconds counter")
            uptime = self.last_heartbeat.get("uptime_seconds", 0)
            metrics.append(f"recorder_uptime_seconds {uptime:.0f}")

            # Error count - total number of errors (red LED activations)
            metrics.append(
                "# HELP recorder_error_count Total errors since service start",
            )
            metrics.append("# TYPE recorder_error_count counter")
            error_count = self.last_heartbeat.get("error_count", 0)
            metrics.append(f"recorder_error_count {error_count}")

            # Restart count - total service restarts (persistent)
            metrics.append(
                "# HELP recorder_restart_count Total service restarts",
            )
            metrics.append("# TYPE recorder_restart_count counter")
            restart_count = self.last_heartbeat.get("restart_count", 0)
            metrics.append(f"recorder_restart_count {restart_count}")

            # Internet connectivity status
            metrics.append(
                "# HELP recorder_internet_connected Internet connectivity status",
            )
            metrics.append("# TYPE recorder_internet_connected gauge")
            internet_connected = (
                1 if self.last_heartbeat.get("internet_connected") else 0
            )
            metrics.append(f"recorder_internet_connected {internet_connected}")

        # Storage metrics - disk space and video counts
        try:
            stats = self.storage.get_stats()

            # Disk space - free bytes and usage ratio
            metrics.append("# HELP recorder_disk_free_bytes Free disk space")
            metrics.append("# TYPE recorder_disk_free_bytes gauge")
            metrics.append(f"recorder_disk_free_bytes {stats.free_space_bytes}")

            metrics.append(
                "# HELP recorder_disk_usage_ratio Disk usage ratio (0-1)",
            )
            metrics.append("# TYPE recorder_disk_usage_ratio gauge")
            metrics.append(
                f"recorder_disk_usage_ratio {stats.space_usage_percent / 100:.3f}",
            )

            # Video counts - labeled by status
            metrics.append("# HELP recorder_videos_total Total videos by status")
            metrics.append("# TYPE recorder_videos_total gauge")
            metrics.append(
                f'recorder_videos_total{{status="pending"}} {stats.pending_count}',
            )
            metrics.append(
                f'recorder_videos_total{{status="completed"}} '
                f"{stats.completed_count}",
            )
            metrics.append(
                f'recorder_videos_total{{status="failed"}} {stats.failed_count}',
            )
            metrics.append(
                f'recorder_videos_total{{status="corrupted"}} '
                f"{stats.corrupted_count}",
            )

            # Upload success rate - percentage of successful uploads
            total_uploads = stats.completed_count + stats.failed_count
            if total_uploads > 0:
                success_rate = stats.completed_count / total_uploads
            else:
                success_rate = 1.0  # No uploads yet = 100% success

            metrics.append(
                "# HELP recorder_upload_success_rate Upload success rate (0-1)",
            )
            metrics.append("# TYPE recorder_upload_success_rate gauge")
            metrics.append(f"recorder_upload_success_rate {success_rate:.3f}")

        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")

        return "\n".join(metrics) + "\n"


class MetricsHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for metrics endpoint.

    Serves Prometheus metrics at /metrics path.
    Returns 404 for all other paths.
    """

    exporter: Optional[MetricsExporter] = None  # Set by server

    def do_GET(self):
        """Handle GET requests for /metrics endpoint."""
        if self.path == "/metrics":
            try:
                metrics = self.exporter.generate_metrics()
                self.send_response(200)
                self.send_header("Content-type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(metrics.encode("utf-8"))
            except Exception as e:
                logger.error(f"Error generating metrics: {e}", exc_info=True)
                self.send_error(500, str(e))
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        """Suppress HTTP request logs (too noisy for metrics scraping)."""


def run_server():
    """
    Run metrics HTTP server.

    Starts HTTP server on METRICS_PORT, serving Prometheus metrics
    at /metrics endpoint. Runs until interrupted.

    The server is single-threaded (one request at a time), which is
    fine for Prometheus scraping (typically 15-60 second intervals).
    """
    exporter = MetricsExporter()
    MetricsHandler.exporter = exporter

    # Bind to all interfaces for Prometheus scraping from any network
    server = HTTPServer(("0.0.0.0", METRICS_PORT), MetricsHandler)  # noqa: S104
    logger.info(f"Metrics server listening on port {METRICS_PORT}")
    logger.info(f"Metrics available at http://localhost:{METRICS_PORT}/metrics")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Metrics server stopped")
        server.shutdown()


if __name__ == "__main__":
    run_server()
