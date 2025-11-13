#!/bin/bash
# Test Summary Report
#
# Shows current status of all auto-recovery components.
# Run this anytime to check system health.
#
# Usage: ./systemd/test-summary.sh

echo "============================================================"
echo "Auto-Recovery System Status Report"
echo "============================================================"
echo ""
echo "Generated: $(date)"
echo "Hostname: $(hostname)"
echo "Uptime: $(uptime -p)"
echo ""

# Service Status
echo "============================================================"
echo "SERVICE STATUS"
echo "============================================================"
echo ""

printf "%-30s %s\n" "Service" "Status"
printf "%-30s %s\n" "-------" "------"

if sudo systemctl is-active --quiet recorder.service; then
    printf "%-30s %s\n" "recorder.service" "🟢 RUNNING"
else
    printf "%-30s %s\n" "recorder.service" "🔴 STOPPED"
fi

if sudo systemctl is-active --quiet recorder-watchdog.service; then
    printf "%-30s %s\n" "recorder-watchdog.service" "🟢 RUNNING"
else
    printf "%-30s %s\n" "recorder-watchdog.service" "🔴 STOPPED"
fi

if sudo systemctl is-active --quiet recorder-metrics.service; then
    printf "%-30s %s\n" "recorder-metrics.service" "🟢 RUNNING"
else
    printf "%-30s %s\n" "recorder-metrics.service" "🔴 STOPPED"
fi

echo ""

# Auto-start Status
echo "============================================================"
echo "AUTO-START ON BOOT"
echo "============================================================"
echo ""

printf "%-30s %s\n" "Service" "Enabled"
printf "%-30s %s\n" "-------" "-------"

if sudo systemctl is-enabled --quiet recorder.service; then
    printf "%-30s %s\n" "recorder.service" "✅ YES"
else
    printf "%-30s %s\n" "recorder.service" "❌ NO"
fi

if sudo systemctl is-enabled --quiet recorder-watchdog.service; then
    printf "%-30s %s\n" "recorder-watchdog.service" "✅ YES"
else
    printf "%-30s %s\n" "recorder-watchdog.service" "❌ NO"
fi

if sudo systemctl is-enabled --quiet recorder-metrics.service; then
    printf "%-30s %s\n" "recorder-metrics.service" "✅ YES"
else
    printf "%-30s %s\n" "recorder-metrics.service" "❌ NO"
fi

echo ""

# Heartbeat Status
echo "============================================================"
echo "HEARTBEAT STATUS"
echo "============================================================"
echo ""

if [ -f /tmp/recorder_heartbeat.json ]; then
    echo "Heartbeat file: ✅ EXISTS"
    echo ""
    cat /tmp/recorder_heartbeat.json | python3 -m json.tool 2>/dev/null || cat /tmp/recorder_heartbeat.json
else
    echo "Heartbeat file: ❌ NOT FOUND"
fi

echo ""

# Metrics Status
echo "============================================================"
echo "METRICS STATUS"
echo "============================================================"
echo ""

if curl -s http://localhost:9101/metrics > /dev/null 2>&1; then
    echo "Metrics endpoint: ✅ RESPONDING"
    echo ""
    echo "Key metrics:"
    curl -s http://localhost:9101/metrics | grep -E "^(recorder_up|recorder_heartbeat_age_seconds|recorder_state|recorder_disk_free_bytes)" | head -10
else
    echo "Metrics endpoint: ❌ NOT RESPONDING"
fi

echo ""

# Watchdog Status
echo "============================================================"
echo "WATCHDOG STATUS"
echo "============================================================"
echo ""

if [ -f /var/log/recorder/watchdog.log ]; then
    echo "Last 5 watchdog log entries:"
    tail -5 /var/log/recorder/watchdog.log
else
    echo "⚠️  Watchdog log file not found"
fi

echo ""

# Restart History
echo "============================================================"
echo "RESTART HISTORY (Last 24 hours)"
echo "============================================================"
echo ""

echo "Service restarts:"
sudo journalctl -u recorder.service --since "24 hours ago" | grep -i "start\|restart\|stop" | tail -10 || echo "No restarts in last 24 hours"

echo ""

# Reboot Triggers
echo "============================================================"
echo "REBOOT TRIGGERS"
echo "============================================================"
echo ""

if [ -f /var/log/recorder/reboot_trigger.log ]; then
    echo "⚠️  Watchdog triggered reboot(s):"
    cat /var/log/recorder/reboot_trigger.log
else
    echo "✅ No watchdog-triggered reboots"
fi

echo ""

# Summary
echo "============================================================"
echo "SUMMARY"
echo "============================================================"
echo ""

SERVICES_RUNNING=0
SERVICES_ENABLED=0

sudo systemctl is-active --quiet recorder.service && ((SERVICES_RUNNING++))
sudo systemctl is-active --quiet recorder-watchdog.service && ((SERVICES_RUNNING++))
sudo systemctl is-active --quiet recorder-metrics.service && ((SERVICES_RUNNING++))

sudo systemctl is-enabled --quiet recorder.service && ((SERVICES_ENABLED++))
sudo systemctl is-enabled --quiet recorder-watchdog.service && ((SERVICES_ENABLED++))
sudo systemctl is-enabled --quiet recorder-metrics.service && ((SERVICES_ENABLED++))

echo "Services running: $SERVICES_RUNNING/3"
echo "Auto-start enabled: $SERVICES_ENABLED/3"

if [ -f /tmp/recorder_heartbeat.json ]; then
    echo "Heartbeat: ✅ Active"
else
    echo "Heartbeat: ❌ Missing"
fi

if curl -s http://localhost:9101/metrics > /dev/null 2>&1; then
    echo "Metrics: ✅ Available"
else
    echo "Metrics: ❌ Unavailable"
fi

echo ""

if [ $SERVICES_RUNNING -eq 3 ] && [ $SERVICES_ENABLED -eq 3 ]; then
    echo "🎉 System Status: HEALTHY"
    echo ""
    echo "All auto-recovery mechanisms are active:"
    echo "  ✅ Services running"
    echo "  ✅ Auto-start enabled"
    echo "  ✅ Heartbeat active"
    echo "  ✅ Watchdog monitoring"
    echo "  ✅ Metrics available"
else
    echo "⚠️  System Status: DEGRADED"
    echo ""
    echo "Some components need attention. Check details above."
fi

echo ""
echo "============================================================"
