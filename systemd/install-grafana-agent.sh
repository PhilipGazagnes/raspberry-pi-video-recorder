#!/bin/bash
# Grafana Agent Installation Script
#
# Installs Grafana Agent to ship metrics and logs to Grafana Cloud.
# Requires Grafana Cloud credentials (see GRAFANA-CLOUD-SETUP.md).
#
# Usage:
#   ./systemd/install-grafana-agent.sh

set -e  # Exit on error

echo "============================================================"
echo "Installing Grafana Agent"
echo "============================================================"
echo ""

# Check credentials file exists
CREDS_FILE="credentials/grafana/cloud-credentials.txt"
if [ ! -f "$CREDS_FILE" ]; then
    echo "❌ Credentials file not found: $CREDS_FILE"
    echo ""
    echo "Please complete Grafana Cloud setup first:"
    echo "  1. See systemd/GRAFANA-CLOUD-SETUP.md"
    echo "  2. Create credentials file with your Grafana Cloud details"
    echo ""
    exit 1
fi

echo "✅ Found credentials file"
echo ""

# Load credentials
echo "Loading Grafana Cloud credentials..."
source "$CREDS_FILE"

# Verify required variables
REQUIRED_VARS=("PROMETHEUS_URL" "PROMETHEUS_USERNAME" "PROMETHEUS_PASSWORD" "LOKI_URL" "LOKI_USERNAME" "LOKI_PASSWORD" "INSTANCE_LABEL")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "❌ Missing required credentials:"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "Please update $CREDS_FILE with all required values."
    exit 1
fi

echo "✅ Credentials validated"
echo ""

# Detect architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

case "$ARCH" in
    armv7l)
        AGENT_ARCH="armv7"
        ;;
    aarch64)
        AGENT_ARCH="arm64"
        ;;
    x86_64)
        AGENT_ARCH="amd64"
        ;;
    *)
        echo "❌ Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

echo "Using Grafana Agent architecture: $AGENT_ARCH"
echo ""

# Grafana Agent version
VERSION="v0.40.2"
FILENAME="grafana-agent-linux-${AGENT_ARCH}.zip"
DOWNLOAD_URL="https://github.com/grafana/agent/releases/download/${VERSION}/${FILENAME}"

echo "Step 1: Downloading Grafana Agent ${VERSION}..."
cd /tmp
wget -q --show-progress "$DOWNLOAD_URL" || {
    echo "❌ Download failed"
    exit 1
}
echo "✅ Downloaded"
echo ""

echo "Step 2: Extracting..."
unzip -q "$FILENAME"
echo "✅ Extracted"
echo ""

echo "Step 3: Installing to /usr/local/bin..."
sudo cp grafana-agent-linux-${AGENT_ARCH} /usr/local/bin/grafana-agent
sudo chmod +x /usr/local/bin/grafana-agent
echo "✅ Installed"
echo ""

echo "Step 4: Cleaning up..."
rm grafana-agent-linux-${AGENT_ARCH}
rm "$FILENAME"
echo "✅ Cleaned up"
echo ""

echo "Step 5: Creating configuration directory..."
sudo mkdir -p /etc/grafana-agent
echo "✅ Created /etc/grafana-agent"
echo ""

echo "Step 6: Generating configuration..."
CURRENT_USER=$(whoami)

# Create Grafana Agent config with credentials
sudo tee /etc/grafana-agent/config.yaml > /dev/null <<EOF
server:
  log_level: info

metrics:
  global:
    scrape_interval: 15s
    remote_write:
      - url: ${PROMETHEUS_URL}
        basic_auth:
          username: ${PROMETHEUS_USERNAME}
          password: ${PROMETHEUS_PASSWORD}

  configs:
    - name: recorder
      scrape_configs:
        # Node Exporter (system metrics: CPU, RAM, disk, temp)
        - job_name: 'node'
          static_configs:
            - targets: ['localhost:9100']
              labels:
                instance: '${INSTANCE_LABEL}'
                customer: '${CUSTOMER_LABEL:-unknown}'
                location: '${LOCATION_LABEL:-unknown}'

        # Recorder app metrics
        - job_name: 'recorder'
          static_configs:
            - targets: ['localhost:9101']
              labels:
                instance: '${INSTANCE_LABEL}'
                customer: '${CUSTOMER_LABEL:-unknown}'
                location: '${LOCATION_LABEL:-unknown}'

logs:
  configs:
    - name: recorder
      clients:
        - url: ${LOKI_URL}
          basic_auth:
            username: ${LOKI_USERNAME}
            password: ${LOKI_PASSWORD}

      positions:
        filename: /tmp/grafana-agent-positions.yaml

      scrape_configs:
        # Recorder service logs
        - job_name: recorder-service
          static_configs:
            - targets: [localhost]
              labels:
                job: recorder-service
                instance: ${INSTANCE_LABEL}
                __path__: /var/log/recorder/service.log

        # Watchdog logs
        - job_name: watchdog
          static_configs:
            - targets: [localhost]
              labels:
                job: watchdog
                instance: ${INSTANCE_LABEL}
                __path__: /var/log/recorder/watchdog.log

        # System logs (optional - can be noisy)
        # Uncomment to enable:
        # - job_name: syslog
        #   static_configs:
        #     - targets: [localhost]
        #       labels:
        #         job: syslog
        #         instance: ${INSTANCE_LABEL}
        #         __path__: /var/log/syslog
EOF

echo "✅ Configuration created"
echo ""

echo "Step 7: Creating systemd service..."
sudo tee /etc/systemd/system/grafana-agent.service > /dev/null <<EOF
[Unit]
Description=Grafana Agent
Documentation=https://grafana.com/docs/agent/
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
ExecStart=/usr/local/bin/grafana-agent -config.file=/etc/grafana-agent/config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created"
echo ""

echo "Step 8: Enabling and starting service..."
sudo systemctl daemon-reload
sudo systemctl enable grafana-agent.service
sudo systemctl start grafana-agent.service
echo "✅ Service started"
echo ""

echo "Step 9: Verifying installation..."
sleep 3

if sudo systemctl is-active --quiet grafana-agent.service; then
    echo "✅ Grafana Agent is running"
else
    echo "❌ Grafana Agent failed to start"
    echo ""
    echo "Checking logs..."
    sudo journalctl -u grafana-agent.service -n 20 --no-pager
    exit 1
fi

echo ""
echo "Step 10: Checking logs for errors..."
sleep 2
ERRORS=$(sudo journalctl -u grafana-agent.service --since "1 minute ago" | grep -i error | wc -l)

if [ "$ERRORS" -eq 0 ]; then
    echo "✅ No errors in logs"
else
    echo "⚠️  Found $ERRORS error(s) in logs:"
    sudo journalctl -u grafana-agent.service --since "1 minute ago" | grep -i error
    echo ""
    echo "Check configuration if errors persist."
fi

echo ""
echo "============================================================"
echo "✅ Grafana Agent Installation Complete!"
echo "============================================================"
echo ""
echo "Metrics and logs are now being shipped to Grafana Cloud!"
echo ""
echo "Instance: $INSTANCE_LABEL"
echo "Customer: ${CUSTOMER_LABEL:-unknown}"
echo "Location: ${LOCATION_LABEL:-unknown}"
echo ""
echo "What's being monitored:"
echo "  📊 Metrics:"
echo "     • System metrics (CPU, RAM, disk, temp) from port 9100"
echo "     • Recorder metrics (state, uploads, etc) from port 9101"
echo "  📝 Logs:"
echo "     • /var/log/recorder/service.log"
echo "     • /var/log/recorder/watchdog.log"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status grafana-agent.service"
echo "  sudo systemctl restart grafana-agent.service"
echo "  sudo journalctl -u grafana-agent.service -f"
echo ""
echo "Next steps:"
echo "  1. Log into Grafana Cloud: https://grafana.com"
echo "  2. Wait 1-2 minutes for first data to arrive"
echo "  3. Create dashboards (see PEACE_OF_MIND.md Task 2.4)"
echo ""
