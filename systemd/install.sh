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
    echo "❌ Error: Must run from project directory"
    echo "   Current directory: $(pwd)"
    echo "   Expected files: recorder_service.py, watchdog.py, etc."
    exit 1
fi

CURRENT_USER=$(whoami)

echo "Step 1: Creating log directory..."
sudo mkdir -p /var/log/recorder
sudo chown $CURRENT_USER:$CURRENT_USER /var/log/recorder
echo "✅ Log directory created for user: $CURRENT_USER"
echo ""

echo "Step 2: Installing systemd service files..."
# Substitute current user and working directory into service files
CURRENT_DIR=$(pwd)

# Create temporary service files with substituted values
sed -e "s|User=philip|User=$CURRENT_USER|g" \
    -e "s|/opt/raspberry-pi-video-recorder|$CURRENT_DIR|g" \
    systemd/recorder.service | sudo tee /etc/systemd/system/recorder.service > /dev/null

sed -e "s|User=philip|User=$CURRENT_USER|g" \
    -e "s|/opt/raspberry-pi-video-recorder|$CURRENT_DIR|g" \
    systemd/recorder-watchdog.service | sudo tee /etc/systemd/system/recorder-watchdog.service > /dev/null

sed -e "s|User=philip|User=$CURRENT_USER|g" \
    -e "s|/opt/raspberry-pi-video-recorder|$CURRENT_DIR|g" \
    systemd/recorder-metrics.service | sudo tee /etc/systemd/system/recorder-metrics.service > /dev/null

echo "✅ Service files installed for user: $CURRENT_USER"
echo "✅ Working directory: $CURRENT_DIR"
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
echo "1. Configure watchdog sudo permissions:"
echo ""
echo "   sudo visudo -f /etc/sudoers.d/recorder-watchdog"
echo ""
echo "   Then paste these lines:"
echo "   ----------------------------------------"
echo "   $CURRENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl restart recorder.service"
echo "   $CURRENT_USER ALL=(ALL) NOPASSWD: /bin/systemctl status recorder.service"
echo "   $CURRENT_USER ALL=(ALL) NOPASSWD: /sbin/reboot"
echo "   ----------------------------------------"
echo ""
echo "2. Test auto-recovery (see systemd/TESTING.md)"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status recorder.service"
echo "  sudo systemctl restart recorder.service"
echo "  sudo journalctl -u recorder.service -f"
echo "  tail -f /var/log/recorder/service.log"
echo ""
