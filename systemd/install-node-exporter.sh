#!/bin/bash
# Node Exporter Installation Script
#
# Installs Prometheus Node Exporter for system metrics collection.
# Provides CPU, RAM, disk, temperature, and other system-level metrics.
#
# Usage:
#   ./systemd/install-node-exporter.sh

set -e  # Exit on error

echo "============================================================"
echo "Installing Prometheus Node Exporter"
echo "============================================================"
echo ""

# Detect architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

# Map architecture to Node Exporter naming
case "$ARCH" in
    armv7l)
        NODE_ARCH="armv7"
        ;;
    aarch64)
        NODE_ARCH="arm64"
        ;;
    x86_64)
        NODE_ARCH="amd64"
        ;;
    *)
        echo "❌ Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

echo "Using Node Exporter architecture: $NODE_ARCH"
echo ""

# Node Exporter version (update as needed)
VERSION="1.7.0"
FILENAME="node_exporter-${VERSION}.linux-${NODE_ARCH}.tar.gz"
DOWNLOAD_URL="https://github.com/prometheus/node_exporter/releases/download/v${VERSION}/${FILENAME}"

echo "Step 1: Downloading Node Exporter v${VERSION}..."
cd /tmp
wget -q --show-progress "$DOWNLOAD_URL" || {
    echo "❌ Download failed"
    exit 1
}
echo "✅ Downloaded"
echo ""

echo "Step 2: Extracting..."
tar xzf "$FILENAME"
echo "✅ Extracted"
echo ""

echo "Step 3: Installing to /usr/local/bin..."
sudo cp node_exporter-${VERSION}.linux-${NODE_ARCH}/node_exporter /usr/local/bin/
sudo chmod +x /usr/local/bin/node_exporter
echo "✅ Installed"
echo ""

echo "Step 4: Cleaning up..."
rm -rf node_exporter-${VERSION}.linux-${NODE_ARCH}
rm "$FILENAME"
echo "✅ Cleaned up"
echo ""

echo "Step 5: Creating systemd service..."
CURRENT_USER=$(whoami)

sudo tee /etc/systemd/system/node-exporter.service > /dev/null <<EOF
[Unit]
Description=Prometheus Node Exporter
Documentation=https://github.com/prometheus/node_exporter
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
ExecStart=/usr/local/bin/node_exporter
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created"
echo ""

echo "Step 6: Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable node-exporter.service
sudo systemctl start node-exporter.service
echo "✅ Service started"
echo ""

echo "Step 7: Verifying installation..."
sleep 2

if sudo systemctl is-active --quiet node-exporter.service; then
    echo "✅ Node Exporter is running"
else
    echo "❌ Node Exporter failed to start"
    sudo systemctl status node-exporter.service --no-pager
    exit 1
fi

# Test metrics endpoint
if curl -s http://localhost:9100/metrics > /dev/null; then
    echo "✅ Metrics endpoint responding"
    echo ""
    echo "Sample metrics:"
    curl -s http://localhost:9100/metrics | head -20
else
    echo "❌ Metrics endpoint not responding"
    exit 1
fi

echo ""
echo "============================================================"
echo "✅ Node Exporter Installation Complete!"
echo "============================================================"
echo ""
echo "Metrics available at: http://localhost:9100/metrics"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status node-exporter.service"
echo "  sudo systemctl restart node-exporter.service"
echo "  curl http://localhost:9100/metrics | grep node_"
echo ""
echo "Key metrics exported:"
echo "  • node_cpu_seconds_total       - CPU usage"
echo "  • node_memory_MemAvailable_bytes - Available RAM"
echo "  • node_filesystem_avail_bytes  - Disk space available"
echo "  • node_hwmon_temp_celsius      - Temperature (if available)"
echo "  • node_load1, node_load5       - System load average"
echo ""
