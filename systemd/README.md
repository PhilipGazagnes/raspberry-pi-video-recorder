# Systemd Services for Recorder

This directory contains systemd service files for running the recorder as a system service with auto-start on boot and auto-recovery.

## Overview

**Three services work together:**

1. **recorder.service** - Main video recorder
   - Runs `recorder_service.py`
   - Auto-restarts on crash (systemd)
   - Writes heartbeat every second

2. **recorder-watchdog.service** - Heartbeat monitor
   - Runs `watchdog.py`
   - Monitors heartbeat file
   - Restarts recorder if frozen
   - Triggers reboot if unrecoverable

3. **recorder-metrics.service** - Metrics exporter
   - Runs `metrics_exporter.py`
   - Exposes Prometheus metrics on port 9101
   - Used for monitoring and dashboards

## Files

```
systemd/
├── recorder.service              # Main service definition
├── recorder-watchdog.service     # Watchdog service definition
├── recorder-metrics.service      # Metrics exporter service definition
├── sudoers.conf                  # Sudo permissions for watchdog
├── install.sh                    # Installation script
├── TESTING.md                    # Testing guide
└── README.md                     # This file
```

## Installation

### Quick Install (Recommended)

```bash
cd /opt/raspberry-pi-video-recorder
chmod +x systemd/install.sh
./systemd/install.sh
```

This will:
1. Create `/var/log/recorder` directory
2. Copy service files to `/etc/systemd/system/`
3. Reload systemd
4. Enable services (auto-start on boot)
5. Start services
6. Show status

### Manual Install

If you prefer to install manually:

```bash
# Create log directory
sudo mkdir -p /var/log/recorder
sudo chown philip:philip /var/log/recorder

# Copy service files
sudo cp systemd/recorder.service /etc/systemd/system/
sudo cp systemd/recorder-watchdog.service /etc/systemd/system/
sudo cp systemd/recorder-metrics.service /etc/systemd/system/

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
```

### Configure Watchdog Permissions

The watchdog needs sudo permissions to restart services and reboot:

```bash
# Create sudoers file (ALWAYS use visudo!)
sudo visudo -f /etc/sudoers.d/recorder-watchdog

# Paste contents from systemd/sudoers.conf
# Then save and exit (Ctrl+X, Y, Enter in nano)
```

**Contents to paste:**
```
philip ALL=(ALL) NOPASSWD: /bin/systemctl restart recorder.service
philip ALL=(ALL) NOPASSWD: /bin/systemctl status recorder.service
philip ALL=(ALL) NOPASSWD: /sbin/reboot
```

## Verification

Check all services are running:

```bash
sudo systemctl status recorder.service
sudo systemctl status recorder-watchdog.service
sudo systemctl status recorder-metrics.service
```

All should show `active (running)` in green.

Check heartbeat:
```bash
cat /tmp/recorder_heartbeat.json
```

Check metrics:
```bash
curl http://localhost:9101/metrics | head -20
```

## Common Commands

### Service Control

```bash
# Start services
sudo systemctl start recorder.service

# Stop services
sudo systemctl stop recorder.service

# Restart services
sudo systemctl restart recorder.service

# Check status
sudo systemctl status recorder.service
```

### View Logs

```bash
# Live logs from systemd journal
sudo journalctl -u recorder.service -f

# Recorder service logs (file)
tail -f /var/log/recorder/service.log

# Watchdog logs
tail -f /var/log/recorder/watchdog.log

# Last 50 lines
sudo journalctl -u recorder.service -n 50
```

### Enable/Disable Auto-start

```bash
# Enable auto-start on boot
sudo systemctl enable recorder.service

# Disable auto-start
sudo systemctl disable recorder.service

# Check if enabled
sudo systemctl is-enabled recorder.service
```

## Auto-Recovery Behavior

### Level 1: Process Crash
- **Trigger**: Service process exits/crashes
- **Recovery**: systemd restarts in 10 seconds
- **Logged in**: journalctl

### Level 2: Process Freeze
- **Trigger**: Heartbeat stale (>30 seconds)
- **Recovery**: Watchdog restarts service
- **Logged in**: `/var/log/recorder/watchdog.log`

### Level 3: Service Unrecoverable
- **Trigger**: 3 restarts within 10 minutes
- **Recovery**: Watchdog triggers system reboot
- **Logged in**: `/var/log/recorder/reboot_trigger.log`

## Testing

See `TESTING.md` for comprehensive testing guide.

Quick smoke test:
```bash
# Kill the process - should restart automatically
sudo kill -9 $(pgrep -f recorder_service.py)
sleep 15
sudo systemctl status recorder.service  # Should be running
```

## Troubleshooting

### Service won't start

```bash
# Check logs for errors
sudo journalctl -u recorder.service -n 50

# Check Python environment
ls -la /opt/raspberry-pi-video-recorder/.venv/bin/python

# Check file permissions
ls -la /opt/raspberry-pi-video-recorder/recorder_service.py

# Try running manually
cd /opt/raspberry-pi-video-recorder
source .venv/bin/activate
python recorder_service.py
```

### Watchdog not restarting service

```bash
# Check watchdog is running
sudo systemctl status recorder-watchdog.service

# Check watchdog logs
tail -f /var/log/recorder/watchdog.log

# Check heartbeat exists
cat /tmp/recorder_heartbeat.json

# Test sudo permissions
sudo systemctl restart recorder.service  # Should work without password
```

### Metrics not responding

```bash
# Check metrics service
sudo systemctl status recorder-metrics.service

# Check port is open
curl http://localhost:9101/metrics

# Check logs
sudo journalctl -u recorder-metrics.service -n 20
```

## Uninstall

To remove the services:

```bash
# Stop services
sudo systemctl stop recorder.service recorder-watchdog.service recorder-metrics.service

# Disable auto-start
sudo systemctl disable recorder.service recorder-watchdog.service recorder-metrics.service

# Remove service files
sudo rm /etc/systemd/system/recorder.service
sudo rm /etc/systemd/system/recorder-watchdog.service
sudo rm /etc/systemd/system/recorder-metrics.service

# Reload systemd
sudo systemctl daemon-reload

# Remove sudoers file
sudo rm /etc/sudoers.d/recorder-watchdog

# Optional: Remove logs
sudo rm -rf /var/log/recorder
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  Raspberry Pi System                                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌────────────────────────────────────────┐       │
│  │  recorder.service                      │       │
│  │  ├─ recorder_service.py                │       │
│  │  ├─ Writes heartbeat every 1s          │       │
│  │  └─ Auto-restart by systemd (10s)      │       │
│  └────────────────────────────────────────┘       │
│         │                                           │
│         │ heartbeat file                            │
│         ↓                                           │
│  ┌────────────────────────────────────────┐       │
│  │  recorder-watchdog.service             │       │
│  │  ├─ watchdog.py                        │       │
│  │  ├─ Monitors heartbeat (every 10s)     │       │
│  │  ├─ Restarts if stale (>30s)           │       │
│  │  └─ Reboots if unrecoverable (3 fails) │       │
│  └────────────────────────────────────────┘       │
│         │                                           │
│         │ reads heartbeat                           │
│         ↓                                           │
│  ┌────────────────────────────────────────┐       │
│  │  recorder-metrics.service              │       │
│  │  ├─ metrics_exporter.py                │       │
│  │  ├─ Reads heartbeat + storage DB       │       │
│  │  └─ HTTP server on port 9101           │       │
│  └────────────────────────────────────────┘       │
│         │                                           │
│         │ Prometheus metrics                        │
│         ↓                                           │
│    http://localhost:9101/metrics                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Next Steps

After installation:
1. ✅ Test auto-recovery (see TESTING.md)
2. ✅ Set up Grafana Cloud monitoring (Phase 2)
3. ✅ Configure alerts
4. ✅ Deploy to production

## Support

For issues or questions:
- Check logs: `sudo journalctl -u recorder.service -f`
- Review TESTING.md for test scenarios
- See main README.md for project documentation
