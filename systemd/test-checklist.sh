#!/bin/bash
# Auto-Recovery Testing Checklist
#
# Quick verification script to ensure all auto-recovery mechanisms work.
# This is a guided checklist - NOT automated tests.
#
# Usage: ./systemd/test-checklist.sh

echo "============================================================"
echo "Auto-Recovery Testing Checklist (Task 1.5)"
echo "============================================================"
echo ""
echo "This script will guide you through testing all auto-recovery"
echo "mechanisms. Follow each test step carefully."
echo ""
read -p "Press Enter to continue..."
echo ""

# Test 1: Verify services are running
echo "============================================================"
echo "PRE-TEST: Verify Services Running"
echo "============================================================"
echo ""

echo "Checking recorder.service..."
if sudo systemctl is-active --quiet recorder.service; then
    echo "✅ recorder.service is running"
else
    echo "❌ recorder.service is NOT running"
    echo "   Fix: sudo systemctl start recorder.service"
    exit 1
fi

echo "Checking recorder-watchdog.service..."
if sudo systemctl is-active --quiet recorder-watchdog.service; then
    echo "✅ recorder-watchdog.service is running"
else
    echo "❌ recorder-watchdog.service is NOT running"
    echo "   Fix: sudo systemctl start recorder-watchdog.service"
    exit 1
fi

echo "Checking recorder-metrics.service..."
if sudo systemctl is-active --quiet recorder-metrics.service; then
    echo "✅ recorder-metrics.service is running"
else
    echo "❌ recorder-metrics.service is NOT running"
    echo "   Fix: sudo systemctl start recorder-metrics.service"
    exit 1
fi

echo ""
echo "Checking heartbeat..."
if [ -f /tmp/recorder_heartbeat.json ]; then
    echo "✅ Heartbeat file exists"
    echo "   Content:"
    cat /tmp/recorder_heartbeat.json | python3 -m json.tool | head -10
else
    echo "❌ Heartbeat file not found"
    exit 1
fi

echo ""
echo "Checking metrics endpoint..."
if curl -s http://localhost:9101/metrics > /dev/null; then
    echo "✅ Metrics endpoint responding"
else
    echo "❌ Metrics endpoint not responding"
    exit 1
fi

echo ""
echo "✅ All pre-tests passed! Ready to test auto-recovery."
echo ""
read -p "Press Enter to continue to Test 1..."
echo ""

# Test 1: Kill Process (systemd auto-restart)
echo "============================================================"
echo "TEST 1: Kill Process (systemd auto-restart)"
echo "============================================================"
echo ""
echo "This test verifies systemd auto-restarts the service on crash."
echo ""
echo "Steps:"
echo "1. Kill the recorder process"
echo "2. Wait 15 seconds"
echo "3. Verify service is running again"
echo ""
read -p "Press Enter to kill the process..."

PID=$(pgrep -f recorder_service.py)
if [ -z "$PID" ]; then
    echo "❌ No recorder process found"
    exit 1
fi

echo "Killing process $PID..."
sudo kill -9 $PID
echo "Process killed. Waiting 15 seconds for systemd to restart..."

for i in {15..1}; do
    echo -ne "  $i seconds remaining...\r"
    sleep 1
done
echo ""

echo "Checking if service restarted..."
if sudo systemctl is-active --quiet recorder.service; then
    echo "✅ TEST 1 PASSED: Service auto-restarted by systemd"
    echo ""
    echo "Recent logs:"
    sudo journalctl -u recorder.service -n 10 --no-pager
else
    echo "❌ TEST 1 FAILED: Service did not restart"
    sudo systemctl status recorder.service --no-pager
    exit 1
fi

echo ""
read -p "Press Enter to continue to Test 2..."
echo ""

# Test 2: Freeze Process (watchdog recovery)
echo "============================================================"
echo "TEST 2: Freeze Process (watchdog recovery)"
echo "============================================================"
echo ""
echo "This test verifies the watchdog detects and recovers frozen service."
echo ""
echo "⚠️  This test takes ~60 seconds to complete."
echo ""
echo "Steps:"
echo "1. Freeze the recorder process (kill -STOP)"
echo "2. Monitor watchdog logs"
echo "3. Wait for watchdog to detect stale heartbeat (~30-40s)"
echo "4. Watchdog restarts service"
echo "5. Verify recovery"
echo ""
read -p "Press Enter to freeze the process..."

PID=$(pgrep -f recorder_service.py)
if [ -z "$PID" ]; then
    echo "❌ No recorder process found"
    exit 1
fi

echo "Freezing process $PID..."
sudo kill -STOP $PID
echo "Process frozen (not killed, just paused)."
echo ""
echo "Monitoring watchdog logs for recovery..."
echo "You should see:"
echo "  - 'Heartbeat stale!' after ~30 seconds"
echo "  - 'Restarting service' shortly after"
echo ""
echo "Watching /var/log/recorder/watchdog.log (Ctrl+C when you see restart)..."
echo ""

# Tail watchdog logs in background
timeout 90 tail -f /var/log/recorder/watchdog.log &
TAIL_PID=$!

# Wait up to 90 seconds for recovery
sleep 90

# Kill the tail process
kill $TAIL_PID 2>/dev/null || true

echo ""
echo "Checking if service recovered..."
if sudo systemctl is-active --quiet recorder.service; then
    echo "✅ TEST 2 PASSED: Watchdog detected freeze and restarted service"

    # Check heartbeat is fresh
    if [ -f /tmp/recorder_heartbeat.json ]; then
        echo "✅ Heartbeat file exists and is fresh"
    fi
else
    echo "❌ TEST 2 FAILED: Service did not recover"
    sudo systemctl status recorder.service --no-pager
    exit 1
fi

echo ""
read -p "Press Enter to continue to Test 3..."
echo ""

# Test 3: Power Loss (auto-start on boot)
echo "============================================================"
echo "TEST 3: Auto-Start on Boot"
echo "============================================================"
echo ""
echo "This test verifies all services auto-start after reboot."
echo ""
echo "⚠️  This will REBOOT the Raspberry Pi!"
echo ""
echo "After reboot:"
echo "1. SSH back in"
echo "2. Run: ./systemd/test-checklist-post-reboot.sh"
echo ""
read -p "Press Enter to REBOOT now, or Ctrl+C to skip..."

echo ""
echo "Rebooting in 5 seconds..."
sleep 5

sudo reboot
