# Task 1.5: Test Auto-Recovery - Quick Guide

**Time**: ~15 minutes
**Location**: Run on Raspberry Pi

---

## Prerequisites

Before testing, ensure services are installed:

```bash
cd /opt/raspberry-pi-video-recorder

# Install services (if not already done)
./systemd/install.sh

# Configure watchdog sudo permissions
sudo visudo -f /etc/sudoers.d/recorder-watchdog
# (paste contents from systemd/sudoers.conf)
```

---

## Option 1: Automated Testing (Recommended)

Run the guided test script:

```bash
cd /opt/raspberry-pi-video-recorder

# Run automated test checklist
./systemd/test-checklist.sh
```

This will guide you through:
- ✅ Test 1: Kill process (systemd auto-restart)
- ✅ Test 2: Freeze process (watchdog recovery)
- ✅ Test 3: Auto-start on boot (triggers reboot)

**After reboot**, SSH back in and run:

```bash
cd /opt/raspberry-pi-video-recorder
./systemd/test-checklist-post-reboot.sh
```

---

## Option 2: Manual Testing

### Test 1: Kill Process (systemd auto-restart)

```bash
# Kill the process
sudo kill -9 $(pgrep -f recorder_service.py)

# Wait 15 seconds
sleep 15

# Check status - should be running again
sudo systemctl status recorder.service
```

**Expected**: ✅ Service auto-restarts in ~10 seconds

---

### Test 2: Freeze Process (watchdog recovery)

```bash
# Freeze the process
sudo kill -STOP $(pgrep -f recorder_service.py)

# Watch watchdog logs
tail -f /var/log/recorder/watchdog.log
```

**Expected**:
- Watchdog detects stale heartbeat after ~30 seconds
- Watchdog restarts service
- Service recovers

**Wait ~60 seconds**, then verify:

```bash
sudo systemctl status recorder.service  # Should be running
cat /tmp/recorder_heartbeat.json        # Should be fresh
```

---

### Test 3: Auto-Start on Boot

```bash
# Reboot
sudo reboot

# After reboot (SSH back in), verify all services started:
sudo systemctl status recorder.service
sudo systemctl status recorder-watchdog.service
sudo systemctl status recorder-metrics.service

# All should show "active (running)" in green
```

**Expected**: ✅ All services auto-start on boot

---

## Health Check Anytime

Run this to check system status anytime:

```bash
./systemd/test-summary.sh
```

Shows:
- Service status (running/stopped)
- Auto-start status (enabled/disabled)
- Heartbeat status
- Metrics status
- Recent restart history
- Overall health summary

---

## Success Criteria

After completing all tests, you should have verified:

- ✅ **Test 1 PASSED**: Service auto-restarts on crash (systemd)
- ✅ **Test 2 PASSED**: Service auto-restarts on freeze (watchdog)
- ✅ **Test 3 PASSED**: All services auto-start on boot

When all tests pass:

```
🎉 Phase 1: Foundation (Auto-Recovery) - COMPLETE!
```

---

## Troubleshooting

### Service won't restart

```bash
# Check logs
sudo journalctl -u recorder.service -n 50

# Try manual start
sudo systemctl start recorder.service
```

### Watchdog not restarting service

```bash
# Check watchdog is running
sudo systemctl status recorder-watchdog.service

# Check watchdog logs
tail -f /var/log/recorder/watchdog.log

# Verify sudo permissions work
sudo systemctl restart recorder.service  # Should work without password
```

### Services don't auto-start on boot

```bash
# Check if enabled
sudo systemctl is-enabled recorder.service

# Enable if needed
sudo systemctl enable recorder.service
sudo systemctl enable recorder-watchdog.service
sudo systemctl enable recorder-metrics.service
```

---

## Next Steps

After Task 1.5 completes successfully:

1. ✅ **Phase 1 Complete**: Foundation (Auto-Recovery)
2. ⏳ **Phase 2**: Visual Monitoring (Grafana Cloud)
   - See `PEACE_OF_MIND.md` for Phase 2 details

---

## Quick Commands Reference

```bash
# Check all services
sudo systemctl status recorder.service recorder-watchdog.service recorder-metrics.service

# View logs
sudo journalctl -u recorder.service -f
tail -f /var/log/recorder/watchdog.log

# Check heartbeat
cat /tmp/recorder_heartbeat.json

# Check metrics
curl http://localhost:9101/metrics | head -20

# System health
./systemd/test-summary.sh
```

---

**Good luck with testing!** 🚀
