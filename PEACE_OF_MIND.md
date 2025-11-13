# Peace of Mind: Production Monitoring System

**Complete guide for deploying a professional monitoring stack for your Raspberry Pi video recorder at Balaruc-les-Bains.**

---

## 🎯 Goals

- ✅ Remote management from anywhere (no on-site visits)
- ✅ Visual dashboards showing system health
- ✅ Auto-recovery (service restart → device reboot)
- ✅ Auto-start on boot (unplug/replug safe)
- ✅ Real-time alerts when issues occur
- ✅ **Cost: €0/month** (Grafana Cloud free tier)

---

## 📋 System Overview

```
┌──────────────────────────────────────────────────────┐
│  Raspberry Pi @ Balaruc-les-Bains Gym                │
│  User: philip                                        │
│  Location: /opt/raspberry-pi-video-recorder         │
├──────────────────────────────────────────────────────┤
│  recorder_service.py                                 │
│  ├─ Heartbeat file (every 10s)                       │
│  └─ Metrics endpoint (:9101)                         │
│                                                      │
│  watchdog.py (monitors heartbeat)                   │
│  metrics_exporter.py (app metrics)                  │
│  node_exporter (system metrics)                     │
│  grafana-agent (ships to cloud)                     │
│                                                      │
│  systemd services (auto-start on boot)              │
└──────────────────────────────────────────────────────┘
                    ↓ push metrics & logs
┌──────────────────────────────────────────────────────┐
│          Grafana Cloud (FREE tier)                   │
│  https://grafana.com                                 │
├──────────────────────────────────────────────────────┤
│  📊 Beautiful Dashboards                             │
│  📝 Live Logs                                        │
│  🚨 Email Alerts                                     │
└──────────────────────────────────────────────────────┘
                    ↓ alerts you
              📧 Your Email
```

---

## 🚀 Implementation Plan

**Total Time: 12-15 hours over 4-5 days**

### Day 1-2: Foundation (Auto-Recovery)
- Add heartbeat to recorder_service.py
- Create watchdog script
- Setup systemd services with auto-restart
- **Result**: Service auto-recovers from freezes

### Day 3-4: Metrics & Cloud (Visual Monitoring)
- Install metrics exporters
- Setup Grafana Cloud (free)
- Create beautiful dashboards
- Configure alerts
- **Result**: Monitor from phone anywhere

### Day 4-5: Polish (Professional Tools)
- Quick status script
- Recovery documentation
- Test all scenarios
- **Result**: Production-ready system

---

## 📝 Phase 1: Foundation (Auto-Recovery)

### Task 1.1: Add Heartbeat to Recorder Service

**File**: `/opt/raspberry-pi-video-recorder/recorder_service.py`

Add these imports at the top:
```python
import json
import os
```

Add to `RecorderService.__init__()` (around line 100):
```python
# Heartbeat setup
self.heartbeat_file = Path("/tmp/recorder_heartbeat.json")
self.last_heartbeat = time.time()
```

Modify `_update_loop()` method (around line 190):
```python
def _update_loop(self):
    """Main update loop - called 10 times per second."""

    # Write heartbeat every second
    current_time = time.time()
    if current_time - self.last_heartbeat >= 1.0:
        self._write_heartbeat()
        self.last_heartbeat = current_time

    # ... existing code (recording health check) ...
```

Add new method to `RecorderService` class:
```python
def _write_heartbeat(self):
    """Write heartbeat for liveness detection."""
    try:
        heartbeat = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.time() - self.state_start_time,
            "state": self.state.value,
            "recording_active": self.current_session is not None,
            "upload_queue_size": self.upload_queue.qsize(),
            "currently_uploading": (
                self.currently_uploading.filename
                if self.currently_uploading else None
            ),
            "pid": os.getpid(),
        }

        # Atomic write (prevent partial reads)
        tmp_file = self.heartbeat_file.with_suffix('.tmp')
        tmp_file.write_text(json.dumps(heartbeat, indent=2))
        tmp_file.rename(self.heartbeat_file)

    except Exception as e:
        # Never crash on heartbeat failure
        self.logger.warning(f"Failed to write heartbeat: {e}")
```

**Lines added**: ~35
**Time**: 15 minutes

---

### Task 1.2: Create Watchdog Script

**File**: `/opt/raspberry-pi-video-recorder/watchdog.py`

Create new file:

```python
#!/usr/bin/env python3
"""
Watchdog for Recorder Service

Monitors heartbeat and restarts service if frozen.
Implements 3-level recovery: restart → multi-restart → reboot
"""

import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Configuration
HEARTBEAT_FILE = Path("/tmp/recorder_heartbeat.json")
HEARTBEAT_TIMEOUT = 30  # seconds
CHECK_INTERVAL = 10  # seconds
MAX_RESTART_ATTEMPTS = 3
RESTART_WINDOW = 600  # 10 minutes

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/recorder/watchdog.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class Watchdog:
    def __init__(self):
        self.restart_count = 0
        self.restart_window_start = time.time()

    def check_heartbeat(self) -> bool:
        """Check if heartbeat is fresh."""
        try:
            if not HEARTBEAT_FILE.exists():
                logger.warning("Heartbeat file not found")
                return False

            heartbeat = json.loads(HEARTBEAT_FILE.read_text())
            timestamp = datetime.fromisoformat(heartbeat['timestamp'])
            age = (datetime.now() - timestamp).total_seconds()

            if age > HEARTBEAT_TIMEOUT:
                logger.error(
                    f"Heartbeat stale! Age: {age:.1f}s, "
                    f"Last state: {heartbeat.get('state', 'unknown')}"
                )
                return False

            logger.debug(f"Heartbeat OK (age: {age:.1f}s)")
            return True

        except Exception as e:
            logger.error(f"Failed to read heartbeat: {e}")
            return False

    def restart_service(self):
        """Restart recorder service."""
        # Reset restart counter if window expired
        if time.time() - self.restart_window_start > RESTART_WINDOW:
            self.restart_count = 0
            self.restart_window_start = time.time()

        self.restart_count += 1
        logger.warning(
            f"Restarting service (attempt {self.restart_count}/{MAX_RESTART_ATTEMPTS})"
        )

        try:
            subprocess.run(
                ['sudo', 'systemctl', 'restart', 'recorder.service'],
                check=True,
                timeout=30
            )
            logger.info("Service restarted successfully")

            # Wait for service to start
            time.sleep(10)

        except subprocess.TimeoutExpired:
            logger.error("Service restart timed out!")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart service: {e}")

    def trigger_reboot(self):
        """Trigger system reboot (last resort)."""
        logger.critical(
            f"Service restart failed {MAX_RESTART_ATTEMPTS} times. "
            "Triggering system reboot..."
        )

        try:
            # Log to separate file for post-mortem
            Path('/var/log/recorder/reboot_trigger.log').write_text(
                f"{datetime.now().isoformat()}\n"
                f"Reason: Service unrecoverable after {MAX_RESTART_ATTEMPTS} restarts\n"
            )

            subprocess.run(['sudo', 'reboot'], check=True, timeout=10)

        except Exception as e:
            logger.critical(f"Failed to trigger reboot: {e}")

    def run(self):
        """Main watchdog loop."""
        logger.info("Watchdog started")

        while True:
            try:
                if not self.check_heartbeat():
                    self.restart_service()

                    # Check if restart worked
                    time.sleep(15)
                    if not self.check_heartbeat():
                        if self.restart_count >= MAX_RESTART_ATTEMPTS:
                            self.trigger_reboot()
                            break

                time.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                logger.info("Watchdog stopped by user")
                break
            except Exception as e:
                logger.error(f"Watchdog error: {e}", exc_info=True)
                time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    watchdog = Watchdog()
    watchdog.run()
```

Make executable:
```bash
chmod +x /opt/raspberry-pi-video-recorder/watchdog.py
```

**Lines**: ~160
**Time**: 30 minutes

---

### Task 1.3: Create Metrics Exporter

**File**: `/opt/raspberry-pi-video-recorder/metrics_exporter.py`

```python
#!/usr/bin/env python3
"""
Metrics Exporter for Recorder Service

Exposes Prometheus-compatible metrics on port 9101.
Reads from heartbeat file and storage database.
"""

import json
import logging
import sys
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from storage import StorageController

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
HEARTBEAT_FILE = Path("/tmp/recorder_heartbeat.json")
METRICS_PORT = 9101


class MetricsExporter:
    def __init__(self):
        self.storage = StorageController()
        self.last_heartbeat = None
        self.heartbeat_age = 999

    def update_metrics(self):
        """Update metrics from heartbeat and database."""
        try:
            # Read heartbeat
            if HEARTBEAT_FILE.exists():
                self.last_heartbeat = json.loads(HEARTBEAT_FILE.read_text())
                timestamp = datetime.fromisoformat(self.last_heartbeat['timestamp'])
                self.heartbeat_age = (datetime.now() - timestamp).total_seconds()
            else:
                self.heartbeat_age = 999
        except Exception as e:
            logger.error(f"Failed to read heartbeat: {e}")
            self.heartbeat_age = 999

    def generate_metrics(self) -> str:
        """Generate Prometheus metrics."""
        self.update_metrics()

        metrics = []

        # Heartbeat metrics
        metrics.append("# HELP recorder_up Whether recorder service is responding")
        metrics.append("# TYPE recorder_up gauge")
        is_up = 1 if self.heartbeat_age < 30 else 0
        metrics.append(f"recorder_up {is_up}")

        metrics.append("# HELP recorder_heartbeat_age_seconds Age of last heartbeat")
        metrics.append("# TYPE recorder_heartbeat_age_seconds gauge")
        metrics.append(f"recorder_heartbeat_age_seconds {self.heartbeat_age:.1f}")

        if self.last_heartbeat:
            # State metrics
            state = self.last_heartbeat.get('state', 'unknown')
            for s in ['booting', 'ready', 'recording', 'processing', 'error']:
                metrics.append(f'recorder_state{{state="{s}"}} {1 if state == s else 0}')

            # Recording metrics
            metrics.append("# HELP recorder_recording_active Whether currently recording")
            metrics.append("# TYPE recorder_recording_active gauge")
            recording = 1 if self.last_heartbeat.get('recording_active') else 0
            metrics.append(f"recorder_recording_active {recording}")

            # Upload queue metrics
            metrics.append("# HELP recorder_upload_queue_size Upload queue depth")
            metrics.append("# TYPE recorder_upload_queue_size gauge")
            queue_size = self.last_heartbeat.get('upload_queue_size', 0)
            metrics.append(f"recorder_upload_queue_size {queue_size}")

            # Uptime
            metrics.append("# HELP recorder_uptime_seconds Service uptime")
            metrics.append("# TYPE recorder_uptime_seconds counter")
            uptime = self.last_heartbeat.get('uptime_seconds', 0)
            metrics.append(f"recorder_uptime_seconds {uptime:.0f}")

        # Storage metrics
        try:
            stats = self.storage.get_storage_stats()

            metrics.append("# HELP recorder_disk_free_bytes Free disk space")
            metrics.append("# TYPE recorder_disk_free_bytes gauge")
            metrics.append(f"recorder_disk_free_bytes {stats.free_space_bytes}")

            metrics.append("# HELP recorder_disk_usage_ratio Disk usage ratio (0-1)")
            metrics.append("# TYPE recorder_disk_usage_ratio gauge")
            metrics.append(f"recorder_disk_usage_ratio {stats.space_usage_percent / 100:.3f}")

            metrics.append("# HELP recorder_videos_total Total videos by status")
            metrics.append("# TYPE recorder_videos_total gauge")
            metrics.append(f'recorder_videos_total{{status="pending"}} {stats.pending_count}')
            metrics.append(f'recorder_videos_total{{status="completed"}} {stats.completed_count}')
            metrics.append(f'recorder_videos_total{{status="failed"}} {stats.failed_count}')
            metrics.append(f'recorder_videos_total{{status="corrupted"}} {stats.corrupted_count}')

            # Calculate success rate
            total_uploads = stats.completed_count + stats.failed_count
            if total_uploads > 0:
                success_rate = stats.completed_count / total_uploads
            else:
                success_rate = 1.0

            metrics.append("# HELP recorder_upload_success_rate Upload success rate (0-1)")
            metrics.append("# TYPE recorder_upload_success_rate gauge")
            metrics.append(f"recorder_upload_success_rate {success_rate:.3f}")

        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")

        return "\n".join(metrics) + "\n"


class MetricsHandler(BaseHTTPRequestHandler):
    exporter = None  # Set by server

    def do_GET(self):
        if self.path == "/metrics":
            try:
                metrics = self.exporter.generate_metrics()
                self.send_response(200)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(metrics.encode('utf-8'))
            except Exception as e:
                logger.error(f"Error generating metrics: {e}", exc_info=True)
                self.send_error(500, str(e))
        else:
            self.send_error(404)

    def log_message(self, format, *args):
        # Suppress HTTP logs
        pass


def run_server():
    """Run metrics HTTP server."""
    exporter = MetricsExporter()
    MetricsHandler.exporter = exporter

    server = HTTPServer(('0.0.0.0', METRICS_PORT), MetricsHandler)
    logger.info(f"Metrics server listening on port {METRICS_PORT}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Metrics server stopped")
        server.shutdown()


if __name__ == "__main__":
    run_server()
```

Make executable:
```bash
chmod +x /opt/raspberry-pi-video-recorder/metrics_exporter.py
```

**Lines**: ~190
**Time**: 45 minutes

---

### Task 1.4: Setup systemd Services

#### Main Recorder Service

**File**: `/etc/systemd/system/recorder.service`

```ini
[Unit]
Description=Raspberry Pi Video Recorder Service
Documentation=https://github.com/yourusername/raspberry-pi-video-recorder
After=network.target

[Service]
Type=simple
User=philip
WorkingDirectory=/opt/raspberry-pi-video-recorder
ExecStart=/opt/raspberry-pi-video-recorder/.venv/bin/python recorder_service.py

# Auto-restart configuration
Restart=on-failure
RestartSec=10
StartLimitBurst=5
StartLimitIntervalSec=600

# Watchdog (belt-and-suspenders with external watchdog)
WatchdogSec=60

# Environment
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

#### Watchdog Service

**File**: `/etc/systemd/system/recorder-watchdog.service`

```ini
[Unit]
Description=Recorder Service Watchdog
Documentation=Monitors recorder service heartbeat and restarts if frozen
After=recorder.service

[Service]
Type=simple
User=philip
WorkingDirectory=/opt/raspberry-pi-video-recorder
ExecStart=/opt/raspberry-pi-video-recorder/.venv/bin/python watchdog.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Metrics Exporter Service

**File**: `/etc/systemd/system/recorder-metrics.service`

```ini
[Unit]
Description=Recorder Metrics Exporter
Documentation=Exposes Prometheus metrics on port 9101
After=recorder.service

[Service]
Type=simple
User=philip
WorkingDirectory=/opt/raspberry-pi-video-recorder
ExecStart=/opt/raspberry-pi-video-recorder/.venv/bin/python metrics_exporter.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Installation Commands

```bash
# Copy service files (run as philip)
sudo cp /opt/raspberry-pi-video-recorder/systemd/*.service /etc/systemd/system/

# OR create them manually with sudo
sudo nano /etc/systemd/system/recorder.service
sudo nano /etc/systemd/system/recorder-watchdog.service
sudo nano /etc/systemd/system/recorder-metrics.service

# Reload systemd
sudo systemctl daemon-reload

# Enable services (auto-start on boot)
sudo systemctl enable recorder.service
sudo systemctl enable recorder-watchdog.service
sudo systemctl enable recorder-metrics.service

# Start services
sudo systemctl start recorder.service
sudo systemctl start recorder-watchdog.service
sudo systemctl start recorder-metrics.service

# Check status
sudo systemctl status recorder.service
sudo systemctl status recorder-watchdog.service
sudo systemctl status recorder-metrics.service
```

#### Grant watchdog sudo permissions

Watchdog needs to restart services and reboot. Add to sudoers:

```bash
# Edit sudoers file
sudo visudo

# Add these lines at the end:
# Allow philip to restart recorder service without password
philip ALL=(ALL) NOPASSWD: /bin/systemctl restart recorder.service
philip ALL=(ALL) NOPASSWD: /bin/systemctl status recorder.service
philip ALL=(ALL) NOPASSWD: /sbin/reboot
```

**Time**: 20 minutes

---

### Task 1.5: Test Auto-Recovery

```bash
# Test 1: Kill service process
sudo kill -9 $(pgrep -f recorder_service.py)
# Expected: systemd restarts it in 10s

# Test 2: Freeze service (simulate hang)
sudo kill -STOP $(pgrep -f recorder_service.py)
# Expected: Watchdog detects stale heartbeat in 30s, restarts service

# Test 3: Check logs
sudo journalctl -u recorder.service -f
tail -f /var/log/recorder/watchdog.log
```

**Time**: 15 minutes

---

## 📊 Phase 2: Visual Monitoring (Grafana Cloud)

### Task 2.1: Install Node Exporter (System Metrics)

```bash
# Download for ARM (Raspberry Pi)
cd /tmp
wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-armv7.tar.gz

# Extract
tar xvfz node_exporter-*.tar.gz

# Install
sudo mv node_exporter-*/node_exporter /usr/local/bin/
sudo chmod +x /usr/local/bin/node_exporter

# Cleanup
rm -rf node_exporter-*

# Create systemd service
sudo tee /etc/systemd/system/node-exporter.service > /dev/null <<'EOF'
[Unit]
Description=Prometheus Node Exporter
Documentation=https://github.com/prometheus/node_exporter
After=network.target

[Service]
User=philip
ExecStart=/usr/local/bin/node_exporter
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable node-exporter.service
sudo systemctl start node-exporter.service

# Test
curl http://localhost:9100/metrics | head -20
```

**Time**: 10 minutes

---

### Task 2.2: Setup Grafana Cloud

1. **Sign up** at https://grafana.com/auth/sign-up/create-user
   - Choose "Free Forever" plan
   - 10k metrics series, 50GB logs/month (plenty for 1 device)

2. **Get connection details**:
   - Go to "My Account" → "Grafana Cloud" → your stack
   - Click "Send Metrics" → choose "Prometheus"
   - Copy the **Remote Write Endpoint** and **credentials**
   - Click "Send Logs" → choose "Loki"
   - Copy the **Loki endpoint** and **credentials**

3. **Save credentials** (you'll need them next)

**Time**: 5 minutes

---

### Task 2.3: Install Grafana Agent

```bash
# Download for ARM
cd /tmp
wget https://github.com/grafana/agent/releases/latest/download/grafana-agent-linux-armv7.zip
unzip grafana-agent-linux-armv7.zip

# Install
sudo mv grafana-agent-linux-armv7 /usr/local/bin/grafana-agent
sudo chmod +x /usr/local/bin/grafana-agent

# Create config directory
sudo mkdir -p /etc/grafana-agent
```

**Create config file**: `/etc/grafana-agent/config.yaml`

**IMPORTANT**: Replace the URLs and credentials with your own from Grafana Cloud!

```yaml
server:
  log_level: info

metrics:
  global:
    scrape_interval: 15s
    remote_write:
      - url: https://prometheus-prod-XX-prod-XX-XX.grafana.net/api/prom/push
        basic_auth:
          username: YOUR_PROMETHEUS_USERNAME
          password: YOUR_PROMETHEUS_PASSWORD

  configs:
    - name: recorder
      scrape_configs:
        # Node Exporter (system metrics: CPU, RAM, disk, temp)
        - job_name: 'node'
          static_configs:
            - targets: ['localhost:9100']
              labels:
                instance: 'balaruc-les-bains-rob'
                customer: 'balaruc-les-bains-rob'
                location: 'gym'

        # Recorder app metrics
        - job_name: 'recorder'
          static_configs:
            - targets: ['localhost:9101']
              labels:
                instance: 'balaruc-les-bains-rob'
                customer: 'balaruc-les-bains-rob'
                location: 'gym'

logs:
  configs:
    - name: recorder
      clients:
        - url: https://logs-prod-XX.grafana.net/loki/api/v1/push
          basic_auth:
            username: YOUR_LOKI_USERNAME
            password: YOUR_LOKI_PASSWORD

      positions:
        filename: /tmp/grafana-agent-positions.yaml

      scrape_configs:
        # Recorder service logs
        - job_name: recorder-service
          static_configs:
            - targets: [localhost]
              labels:
                job: recorder-service
                instance: balaruc-les-bains-rob
                __path__: /var/log/recorder/service.log

        # Watchdog logs
        - job_name: watchdog
          static_configs:
            - targets: [localhost]
              labels:
                job: watchdog
                instance: balaruc-les-bains-rob
                __path__: /var/log/recorder/watchdog.log

        # System logs
        - job_name: syslog
          static_configs:
            - targets: [localhost]
              labels:
                job: syslog
                instance: balaruc-les-bains-rob
                __path__: /var/log/syslog
```

**Create systemd service**: `/etc/systemd/system/grafana-agent.service`

```ini
[Unit]
Description=Grafana Agent
Documentation=https://grafana.com/docs/agent/
After=network.target

[Service]
User=philip
ExecStart=/usr/local/bin/grafana-agent -config.file=/etc/grafana-agent/config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable grafana-agent.service
sudo systemctl start grafana-agent.service

# Check status
sudo systemctl status grafana-agent.service

# Check logs
sudo journalctl -u grafana-agent.service -f
```

**Time**: 20 minutes

---

### Task 2.4: Create Dashboards in Grafana Cloud

1. **Log into your Grafana Cloud instance**

2. **Import Node Exporter Dashboard** (system metrics):
   - Click "+" → "Import Dashboard"
   - Enter ID: `1860`
   - Click "Load"
   - Select your Prometheus data source
   - Click "Import"
   - **Result**: Beautiful CPU, RAM, disk, temperature graphs!

3. **Create Custom Recorder Dashboard**:
   - Click "+" → "Create Dashboard"
   - Add panels for:
     - **Service Status** (gauge): `recorder_up`
     - **Current State** (stat): `recorder_state`
     - **Disk Free** (gauge): `recorder_disk_free_bytes / 1024 / 1024 / 1024` (GB)
     - **Upload Success Rate** (gauge): `recorder_upload_success_rate * 100` (%)
     - **Videos by Status** (pie chart): `recorder_videos_total`
     - **CPU Temperature** (graph): `node_hwmon_temp_celsius`
     - **Memory Usage** (graph): `100 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100)`
     - **Recordings per Day** (graph): `increase(recorder_videos_total{status="completed"}[24h])`

4. **Save dashboard** as "Recorder - Balaruc-les-Bains"

**Time**: 30 minutes

---

### Task 2.5: Setup Alerts

In Grafana Cloud, create these alert rules:

#### Alert 1: Service Down (CRITICAL)
```
Name: Service Down
Condition: recorder_up == 0
For: 1 minute
Severity: Critical
Notification: Email
Message: "🔴 Recorder service is DOWN at Balaruc-les-Bains!"
```

#### Alert 2: Disk Space Low (WARNING)
```
Name: Disk Space Low
Condition: recorder_disk_free_bytes < 5000000000  (5GB)
For: 5 minutes
Severity: Warning
Notification: Email
Message: "⚠️ Low disk space at Balaruc-les-Bains"
```

#### Alert 3: Upload Failures (WARNING)
```
Name: Upload Success Rate Low
Condition: recorder_upload_success_rate < 0.95
For: 1 hour
Severity: Warning
Notification: Email
Message: "⚠️ Upload success rate below 95% at Balaruc-les-Bains"
```

#### Alert 4: High Temperature (WARNING)
```
Name: High Temperature
Condition: node_hwmon_temp_celsius > 80
For: 5 minutes
Severity: Warning
Notification: Email
Message: "🌡️ High temperature (>80°C) at Balaruc-les-Bains"
```

**Time**: 15 minutes

---

## 🛠️ Phase 3: Professional Tools

### Task 3.1: Quick Status Script

**File**: `/opt/raspberry-pi-video-recorder/status.sh`

```bash
#!/bin/bash
# Quick status check - run from your laptop via SSH

echo "=== RECORDER STATUS @ BALARUC-LES-BAINS ==="
echo ""

# Service status
echo "📊 Services:"
systemctl is-active recorder.service && echo "  ✅ Recorder: RUNNING" || echo "  ❌ Recorder: STOPPED"
systemctl is-active recorder-watchdog.service && echo "  ✅ Watchdog: RUNNING" || echo "  ❌ Watchdog: STOPPED"
systemctl is-active recorder-metrics.service && echo "  ✅ Metrics: RUNNING" || echo "  ❌ Metrics: STOPPED"
systemctl is-active node-exporter.service && echo "  ✅ Node Exporter: RUNNING" || echo "  ❌ Node Exporter: STOPPED"
systemctl is-active grafana-agent.service && echo "  ✅ Grafana Agent: RUNNING" || echo "  ❌ Grafana Agent: STOPPED"
echo ""

# Heartbeat
if [ -f /tmp/recorder_heartbeat.json ]; then
    echo "💓 Heartbeat:"
    cat /tmp/recorder_heartbeat.json | python3 -m json.tool | grep -E "state|recording_active|timestamp|uptime_seconds" | head -4
else
    echo "  ❌ No heartbeat found"
fi
echo ""

# Disk space
echo "💾 Disk Space:"
df -h /opt/raspberry-pi-video-recorder | tail -1 | awk '{print "  Free: "$4" / "$2" ("$5" used)"}'
echo ""

# Temperature
if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
    TEMP=$(cat /sys/class/thermal/thermal_zone0/temp)
    TEMP_C=$((TEMP/1000))
    echo "🌡️  Temperature: ${TEMP_C}°C"
    echo ""
fi

# Recent errors (last 5)
echo "📝 Recent Errors (last 5 from past hour):"
sudo journalctl -u recorder.service --since "1 hour ago" -p err -n 5 --no-pager | grep -v "^--" || echo "  ✅ No errors"
echo ""

# Metrics preview
echo "📈 Quick Metrics:"
curl -s http://localhost:9101/metrics 2>/dev/null | grep -E "recorder_up|recorder_state|recorder_videos_total|recorder_disk" | head -10 || echo "  ❌ Metrics not available"
```

Make executable:
```bash
chmod +x /opt/raspberry-pi-video-recorder/status.sh
```

**Usage from laptop** (via Tailscale or direct SSH):
```bash
# Replace with your Tailscale hostname or IP
ssh philip@[TO_BE_COMPLETED] /opt/raspberry-pi-video-recorder/status.sh
```

**Time**: 10 minutes

---

### Task 3.2: Recovery Procedures

**File**: `/opt/raspberry-pi-video-recorder/RECOVERY.md`

```markdown
# Recovery Procedures - Balaruc-les-Bains Recorder

Quick reference for fixing issues remotely.

## Prerequisites

```bash
# SSH via Tailscale (recommended)
ssh philip@[TO_BE_COMPLETED]

# Or direct IP (if on same network)
ssh philip@192.168.X.X
```

---

## Level 1: Restart Service (First Try)

**When**: Service is frozen or stuck

```bash
sudo systemctl restart recorder.service
./status.sh  # Check if it worked
```

**Expected**: Service restarts in ~10 seconds, green LED comes on

---

## Level 2: Check Logs (Diagnose)

**When**: Service keeps failing

```bash
# Live service logs
sudo journalctl -u recorder.service -f

# Recent errors only
sudo journalctl -u recorder.service --since "1 hour ago" -p err

# Watchdog logs
tail -f /var/log/recorder/watchdog.log

# All recorder logs
tail -f /var/log/recorder/service.log
```

**Look for**: Camera errors, disk full, network issues

---

## Level 3: Restart All Services

**When**: Multiple issues or uncertain state

```bash
sudo systemctl restart recorder.service
sudo systemctl restart recorder-watchdog.service
sudo systemctl restart recorder-metrics.service
sudo systemctl restart grafana-agent.service

# Wait 15 seconds
sleep 15

# Check status
./status.sh
```

---

## Level 4: Reboot Device (Last Resort)

**When**: Service completely unresponsive

```bash
sudo reboot
```

**Expected**:
- Device reboots in ~60 seconds
- All services auto-start
- Check status after 2 minutes

---

## Level 5: Update Code (Deploy Fixes)

**When**: You've pushed a fix to git

```bash
cd /opt/raspberry-pi-video-recorder

# Save any local changes (if needed)
git stash

# Pull latest code
git pull origin main

# Apply local changes back (if stashed)
git stash pop

# Restart service
sudo systemctl restart recorder.service

# Verify
./status.sh
```

---

## Level 6: Check Disk Space

**When**: Recording failures or disk alerts

```bash
# Check disk space
df -h /opt/raspberry-pi-video-recorder

# Check video storage
du -sh /opt/raspberry-pi-video-recorder/temp_videos/*

# Manual cleanup (if needed)
cd /opt/raspberry-pi-video-recorder
source .venv/bin/activate
python -c "from storage import StorageController; s = StorageController(); print(f'Deleted {s.cleanup_old_videos(dry_run=False)} videos')"
```

---

## Level 7: Check Camera

**When**: Camera errors in logs

```bash
# List cameras
v4l2-ctl --list-devices

# Test camera
ffmpeg -f v4l2 -i /dev/video0 -frames 1 /tmp/test.jpg

# If camera missing, try reboot
sudo reboot
```

---

## Level 8: Full Reset (Nuclear Option)

**⚠️ DANGER: Only if everything else fails**

```bash
# Stop service
sudo systemctl stop recorder.service

# Backup database
cp /opt/raspberry-pi-video-recorder/temp_videos/video_metadata.db ~/backup_$(date +%F).db

# Clear all videos (CAREFUL!)
rm -rf /opt/raspberry-pi-video-recorder/temp_videos/pending/*
rm -rf /opt/raspberry-pi-video-recorder/temp_videos/uploaded/*
rm -rf /opt/raspberry-pi-video-recorder/temp_videos/failed/*

# Reset code to clean state
cd /opt/raspberry-pi-video-recorder
git fetch origin
git reset --hard origin/main

# Restart
sudo systemctl start recorder.service
./status.sh
```

---

## Emergency: Check if Watchdog Triggered Reboot

```bash
# Check for reboot triggers
cat /var/log/recorder/reboot_trigger.log

# If file exists, it shows when/why watchdog rebooted the system
```

---

## Quick Commands Cheat Sheet

```bash
# Status
./status.sh

# Restart service
sudo systemctl restart recorder.service

# View live logs
sudo journalctl -u recorder.service -f

# Reboot device
sudo reboot

# Update code
cd /opt/raspberry-pi-video-recorder && git pull && sudo systemctl restart recorder.service
```
```

**Time**: 15 minutes

---

## ✅ Final Setup Checklist

Before going to production, verify everything:

```bash
# On the Raspberry Pi

# 1. Check all services are running
sudo systemctl status recorder.service
sudo systemctl status recorder-watchdog.service
sudo systemctl status recorder-metrics.service
sudo systemctl status node-exporter.service
sudo systemctl status grafana-agent.service

# 2. Check all services are enabled (auto-start on boot)
sudo systemctl is-enabled recorder.service
sudo systemctl is-enabled recorder-watchdog.service
sudo systemctl is-enabled recorder-metrics.service
sudo systemctl is-enabled node-exporter.service
sudo systemctl is-enabled grafana-agent.service

# 3. Test heartbeat exists
cat /tmp/recorder_heartbeat.json

# 4. Test metrics endpoints
curl http://localhost:9100/metrics | head  # Node Exporter
curl http://localhost:9101/metrics | head  # Recorder metrics

# 5. Test status script
/opt/raspberry-pi-video-recorder/status.sh

# 6. Check Grafana Cloud dashboards (from browser)
# - Open your Grafana Cloud URL
# - Check metrics are arriving
# - Check logs are arriving

# 7. Test reboot (auto-start verification)
sudo reboot
# Wait 2 minutes, then SSH back in and run:
/opt/raspberry-pi-video-recorder/status.sh
```

---

## 🧪 Testing Scenarios

Before going live, test these failure modes:

### Test 1: Kill Process (systemd auto-restart)
```bash
sudo kill -9 $(pgrep -f recorder_service.py)
sleep 15
./status.sh  # Should show RUNNING
```
**Expected**: Service restarts in 10s

---

### Test 2: Freeze Process (watchdog recovery)
```bash
sudo kill -STOP $(pgrep -f recorder_service.py)
sleep 45
./status.sh  # Should show RUNNING (watchdog restarted it)
```
**Expected**: Watchdog detects stale heartbeat in 30s, restarts service

---

### Test 3: Fill Disk Space
```bash
# Create large file
dd if=/dev/zero of=/opt/raspberry-pi-video-recorder/temp_videos/test.bin bs=1M count=5000
# Try to start recording
# Expected: Service refuses to record, red LED, alert sent
# Cleanup:
rm /opt/raspberry-pi-video-recorder/temp_videos/test.bin
```

---

### Test 4: Disconnect Network
```bash
sudo ifconfig wlan0 down
# Check white LED (should turn off)
# Check dashboard (should show no connectivity)
sudo ifconfig wlan0 up
```

---

### Test 5: Unplug/Replug Power
```bash
# Physically unplug Raspberry Pi
# Wait 10 seconds
# Plug back in
# Wait 2 minutes for boot
ssh philip@[device] /opt/raspberry-pi-video-recorder/status.sh
# Expected: All services running
```

---

## 📱 What You Can Do From Your Phone

1. **Open Grafana Cloud app** (iOS/Android)
   - View real-time dashboard
   - See system health at a glance
   - Check if recording is active
   - Monitor disk space

2. **Receive email alerts**
   - Service down
   - Disk space low
   - Upload failures
   - High temperature

3. **SSH via phone** (using apps like Termius):
   ```bash
   ssh philip@[device]
   /opt/raspberry-pi-video-recorder/status.sh
   ```

4. **Emergency restart**:
   ```bash
   ssh philip@[device] "sudo systemctl restart recorder.service"
   ```

---

## 📊 What You'll See in Grafana

**Dashboard shows**:
- 🟢 Service UP/DOWN indicator
- 🎥 Current state (READY/RECORDING/ERROR)
- 💾 Disk space gauge (color-coded: green/yellow/red)
- 📈 CPU usage graph (last 1 hour)
- 🧠 RAM usage graph
- 🌡️ Temperature graph (with threshold line at 80°C)
- 📊 Upload success rate (%)
- 📹 Videos count by status (pie chart)
- 📉 Recordings per day (trend)
- 🕐 Uptime counter

**Logs panel shows**:
- Live service logs
- Watchdog actions
- Recording events
- Upload results
- Errors highlighted in red

---

## 💰 Cost Breakdown

| Service | Cost | Notes |
|---------|------|-------|
| Grafana Cloud Free | €0/month | 10k series, 50GB logs (enough for 1 device) |
| Tailscale Free | €0/month | 100 devices, 1 user (enough for you) |
| **Total** | **€0/month** | Zero cost! |

**Upgrade paths** (if you scale to 10+ devices):
- Grafana Cloud Pro: ~€10/month (more metrics/logs)
- Self-hosted Prometheus/Grafana: €5/month VPS

---

## 🎯 Success Criteria

✅ You can see system status from your phone
✅ You receive email if service goes down
✅ Service auto-restarts if it freezes
✅ Device auto-reboots if service can't recover
✅ All services auto-start after power loss
✅ You can SSH from anywhere via Tailscale
✅ You can update code remotely via git pull
✅ You never need to visit the gym for repairs

---

## 📞 Support Workflow

**When customer calls: "It's not working"**

1. **Open Grafana dashboard on phone** (30 seconds)
   - See exactly what's wrong
   - Is service running? What state?
   - Disk full? Network down?

2. **SSH from laptop** (1 minute)
   ```bash
   ssh philip@[device] /opt/raspberry-pi-video-recorder/status.sh
   ```

3. **Fix remotely** (2-5 minutes)
   - Restart service
   - Update code
   - Clear disk space
   - Reboot if needed

4. **Verify fix** (30 seconds)
   - Check Grafana dashboard
   - Green LED should be on
   - Customer confirms it works

**Total time**: 5-10 minutes from your couch ☕

---

## 🚀 Next Steps

1. **Day 1-2**: Implement Phase 1 (heartbeat, watchdog, systemd)
2. **Day 3-4**: Implement Phase 2 (Grafana Cloud, dashboards, alerts)
3. **Day 4-5**: Test everything, create documentation
4. **Day 5**: Deploy to production at Balaruc-les-Bains

**Then relax** 😎 - Your monitoring is professional-grade!

---

## 📚 Reference

### File Locations
```
/opt/raspberry-pi-video-recorder/
├── recorder_service.py        # Main service
├── watchdog.py                # Heartbeat monitor (NEW)
├── metrics_exporter.py        # Metrics HTTP server (NEW)
├── status.sh                  # Quick status script (NEW)
├── RECOVERY.md                # Recovery procedures (NEW)
├── temp_videos/               # Video storage
│   ├── pending/
│   ├── uploaded/
│   └── video_metadata.db
├── .venv/                     # Python virtual environment
└── credentials/               # YouTube OAuth tokens

/var/log/recorder/
├── service.log                # Main service logs
├── watchdog.log               # Watchdog logs
└── reboot_trigger.log         # Watchdog reboot events

/etc/systemd/system/
├── recorder.service           # Main service (NEW)
├── recorder-watchdog.service  # Watchdog (NEW)
├── recorder-metrics.service   # Metrics exporter (NEW)
├── node-exporter.service      # System metrics (NEW)
└── grafana-agent.service      # Cloud bridge (NEW)

/tmp/
└── recorder_heartbeat.json    # Live heartbeat file
```

### Ports Used
- **9100**: Node Exporter (system metrics)
- **9101**: Recorder Metrics (app metrics)
- **None external**: All metrics pushed to Grafana Cloud via agent

### Commands Quick Reference
```bash
# Status
/opt/raspberry-pi-video-recorder/status.sh

# Restart service
sudo systemctl restart recorder.service

# View logs
sudo journalctl -u recorder.service -f
tail -f /var/log/recorder/service.log

# Update code
cd /opt/raspberry-pi-video-recorder && git pull && sudo systemctl restart recorder.service

# Reboot
sudo reboot

# Check if auto-start enabled
sudo systemctl is-enabled recorder.service
```

---

## 🎉 Conclusion

You now have a **production-grade monitoring system** that:

- ✅ Auto-recovers from failures (3 levels)
- ✅ Auto-starts on boot
- ✅ Provides visual dashboards
- ✅ Sends alerts when needed
- ✅ Enables remote management
- ✅ Costs €0/month
- ✅ Scales to 100+ devices

**This is what professional IoT companies use.** You're providing a top-quality service from day one! 🚀

---

**Questions? Issues? Updates needed?**
Keep this document updated as you deploy and learn!
