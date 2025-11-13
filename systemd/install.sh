#!/bin/bash
# Systemd Services Installation Script
#
# This script installs and enables the recorder systemd services.
# Run as the philip user (uses sudo for privileged operations).
#
# Usage:
#   ./systemd/install.sh

set -e  # Exit on error

echo "============================================================"
echo "Installing Recorder Systemd Services"
echo "============================================================"
echo ""

# Check we're running from the correct directory
if [ ! -f "recorder_service.py" ]; then
    echo "❌ Error: Must run from /opt/raspberry-pi-video-recorder"
    exit 1
fi

# Check we're the correct user
if [ "$USER" != "philip" ]; then
    echo "⚠️  Warning: Expected user 'philip', but running as '$USER'"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Step 1: Creating log directory..."
sudo mkdir -p /var/log/recorder
sudo chown philip:philip /var/log/recorder
echo "✅ Log directory created"
echo ""

echo "Step 2: Copying systemd service files..."
sudo cp systemd/recorder.service /etc/systemd/system/
sudo cp systemd/recorder-watchdog.service /etc/systemd/system/
sudo cp systemd/recorder-metrics.service /etc/systemd/system/
echo "✅ Service files copied"
echo ""

echo "Step 3: Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "✅ Systemd reloaded"
echo ""

echo "Step 4: Enabling services (auto-start on boot)..."
sudo systemctl enable recorder.service
sudo systemctl enable recorder-watchdog.service
sudo systemctl enable recorder-metrics.service
echo "✅ Services enabled"
echo ""

echo "Step 5: Starting services..."
sudo systemctl start recorder.service
sudo systemctl start recorder-watchdog.service
sudo systemctl start recorder-metrics.service
echo "✅ Services started"
echo ""

echo "Step 6: Checking service status..."
echo ""
echo "--- Recorder Service ---"
sudo systemctl status recorder.service --no-pager || true
echo ""
echo "--- Watchdog Service ---"
sudo systemctl status recorder-watchdog.service --no-pager || true
echo ""
echo "--- Metrics Service ---"
sudo systemctl status recorder-metrics.service --no-pager || true
echo ""

echo "============================================================"
echo "Installation Complete!"
echo "============================================================"
echo ""
echo "Next steps:"
echo "1. Configure watchdog sudo permissions (see systemd/sudoers.conf)"
echo "2. Run: sudo visudo -f /etc/sudoers.d/recorder-watchdog"
echo "3. Paste the contents of systemd/sudoers.conf"
echo "4. Test auto-recovery (see systemd/TESTING.md)"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status recorder.service"
echo "  sudo systemctl restart recorder.service"
echo "  sudo journalctl -u recorder.service -f"
echo "  tail -f /var/log/recorder/service.log"
echo ""
