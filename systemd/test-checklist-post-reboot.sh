#!/bin/bash
# Post-Reboot Testing Script
#
# Run this after rebooting to verify auto-start on boot works.
#
# Usage: ./systemd/test-checklist-post-reboot.sh

echo "============================================================"
echo "POST-REBOOT: Verify Auto-Start on Boot"
echo "============================================================"
echo ""

# Check uptime
UPTIME=$(uptime -p)
echo "System uptime: $UPTIME"
echo ""

# Test 3: Auto-start verification
echo "Checking if all services auto-started..."
echo ""

ALL_PASSED=true

echo "1. Checking recorder.service..."
if sudo systemctl is-active --quiet recorder.service; then
    echo "   ✅ recorder.service is running"
else
    echo "   ❌ recorder.service is NOT running"
    ALL_PASSED=false
fi

echo "2. Checking recorder-watchdog.service..."
if sudo systemctl is-active --quiet recorder-watchdog.service; then
    echo "   ✅ recorder-watchdog.service is running"
else
    echo "   ❌ recorder-watchdog.service is NOT running"
    ALL_PASSED=false
fi

echo "3. Checking recorder-metrics.service..."
if sudo systemctl is-active --quiet recorder-metrics.service; then
    echo "   ✅ recorder-metrics.service is running"
else
    echo "   ❌ recorder-metrics.service is NOT running"
    ALL_PASSED=false
fi

echo ""
echo "4. Checking heartbeat file..."
if [ -f /tmp/recorder_heartbeat.json ]; then
    echo "   ✅ Heartbeat file exists"

    # Check heartbeat age
    TIMESTAMP=$(cat /tmp/recorder_heartbeat.json | python3 -c "import sys, json; print(json.load(sys.stdin)['timestamp'])" 2>/dev/null)
    if [ ! -z "$TIMESTAMP" ]; then
        echo "   Last heartbeat: $TIMESTAMP"
    fi
else
    echo "   ❌ Heartbeat file not found"
    ALL_PASSED=false
fi

echo ""
echo "5. Checking metrics endpoint..."
if curl -s http://localhost:9101/metrics > /dev/null 2>&1; then
    echo "   ✅ Metrics endpoint responding"

    # Check if service is up
    RECORDER_UP=$(curl -s http://localhost:9101/metrics | grep "^recorder_up " | awk '{print $2}')
    if [ "$RECORDER_UP" = "1" ]; then
        echo "   ✅ Service reporting as UP (recorder_up=1)"
    else
        echo "   ⚠️  Service reporting as DOWN (recorder_up=$RECORDER_UP)"
    fi
else
    echo "   ❌ Metrics endpoint not responding"
    ALL_PASSED=false
fi

echo ""
echo "6. Checking auto-start is enabled..."
ENABLED_COUNT=0
if sudo systemctl is-enabled --quiet recorder.service; then
    echo "   ✅ recorder.service auto-start enabled"
    ((ENABLED_COUNT++))
else
    echo "   ❌ recorder.service auto-start NOT enabled"
fi

if sudo systemctl is-enabled --quiet recorder-watchdog.service; then
    echo "   ✅ recorder-watchdog.service auto-start enabled"
    ((ENABLED_COUNT++))
else
    echo "   ❌ recorder-watchdog.service auto-start NOT enabled"
fi

if sudo systemctl is-enabled --quiet recorder-metrics.service; then
    echo "   ✅ recorder-metrics.service auto-start enabled"
    ((ENABLED_COUNT++))
else
    echo "   ❌ recorder-metrics.service auto-start NOT enabled"
fi

echo ""

if [ $ENABLED_COUNT -eq 3 ]; then
    echo "   ✅ All services have auto-start enabled"
else
    echo "   ⚠️  Only $ENABLED_COUNT/3 services have auto-start enabled"
    ALL_PASSED=false
fi

echo ""
echo "============================================================"

if [ "$ALL_PASSED" = true ]; then
    echo "✅ TEST 3 PASSED: All services auto-started on boot!"
    echo "============================================================"
    echo ""
    echo "🎉 ALL TESTS PASSED!"
    echo ""
    echo "Your auto-recovery system is working perfectly:"
    echo "  ✅ Systemd auto-restarts on crash"
    echo "  ✅ Watchdog restarts on freeze"
    echo "  ✅ Services auto-start on boot"
    echo ""
    echo "Phase 1: Foundation (Auto-Recovery) - COMPLETE!"
    echo ""
    echo "Next steps:"
    echo "  - Phase 2: Visual Monitoring (Grafana Cloud)"
    echo "  - See PEACE_OF_MIND.md for details"
else
    echo "❌ TEST 3 FAILED: Some services did not auto-start"
    echo "============================================================"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check service status:"
    echo "     sudo systemctl status recorder.service"
    echo "  2. Check logs:"
    echo "     sudo journalctl -u recorder.service -n 50"
    echo "  3. Try manual start:"
    echo "     sudo systemctl start recorder.service"
    exit 1
fi
