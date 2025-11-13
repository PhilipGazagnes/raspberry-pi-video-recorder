# Testing Auto-Recovery (Task 1.5)

This guide walks through testing all auto-recovery scenarios.

## Prerequisites

Ensure all services are running:
```bash
sudo systemctl status recorder.service
sudo systemctl status recorder-watchdog.service
sudo systemctl status recorder-metrics.service
```

All should show `active (running)` in green.

---

## Test 1: Kill Process (systemd auto-restart)

**Expected**: Systemd restarts service in 10 seconds

```bash
# Kill the recorder process
sudo kill -9 $(pgrep -f recorder_service.py)

# Wait 15 seconds
sleep 15

# Check status - should be running again
sudo systemctl status recorder.service

# Check logs to see the restart
sudo journalctl -u recorder.service -n 20
```

**Success criteria:**
- ✅ Service restarts automatically
- ✅ Status shows `active (running)` after 15 seconds
- ✅ Green LED turns back on

---

## Test 2: Freeze Process (watchdog recovery)

**Expected**: Watchdog detects stale heartbeat and restarts service in ~45 seconds

```bash
# Freeze the recorder process (simulates hang)
sudo kill -STOP $(pgrep -f recorder_service.py)

# Monitor watchdog logs in real-time
tail -f /var/log/recorder/watchdog.log
```

**What you'll see:**
1. Heartbeat becomes stale (~30 seconds)
2. Watchdog logs: "Heartbeat stale! Age: 31.2s"
3. Watchdog restarts service: "Restarting service (attempt 1/3)"
4. Service recovers

```bash
# After ~60 seconds, check service is running
sudo systemctl status recorder.service

# Check heartbeat is fresh
cat /tmp/recorder_heartbeat.json
```

**Success criteria:**
- ✅ Watchdog detects stale heartbeat within 30-40 seconds
- ✅ Watchdog restarts service automatically
- ✅ Service recovers and heartbeat resumes
- ✅ Green LED turns back on

---

## Test 3: Multiple Restart Failures (reboot trigger)

**⚠️ WARNING: This will reboot your Raspberry Pi!**

This test simulates a service that can't recover, triggering system reboot.

**Skip this test unless you want to verify reboot behavior.**

```bash
# Simulate multiple failures by preventing service from starting
# (For testing purposes only - don't do this in production!)

# 1. Stop the service
sudo systemctl stop recorder.service

# 2. Make the service fail to start (rename Python binary temporarily)
sudo mv /opt/raspberry-pi-video-recorder/.venv/bin/python \
        /opt/raspberry-pi-video-recorder/.venv/bin/python.bak

# 3. Start the service (will fail)
sudo systemctl start recorder.service

# 4. Watch watchdog logs
tail -f /var/log/recorder/watchdog.log

# Within 10 minutes, watchdog will trigger reboot after 3 failed restart attempts
# You'll see:
# - "Restarting service (attempt 1/3)"
# - "Restarting service (attempt 2/3)"
# - "Restarting service (attempt 3/3)"
# - "Service restart failed 3 times. Triggering system reboot..."
# - System reboots

# After reboot, restore the Python binary:
sudo mv /opt/raspberry-pi-video-recorder/.venv/bin/python.bak \
        /opt/raspberry-pi-video-recorder/.venv/bin/python

# Check reboot trigger log
cat /var/log/recorder/reboot_trigger.log
```

**Success criteria:**
- ✅ Watchdog attempts 3 restarts
- ✅ After 3rd failure, system reboots
- ✅ Reboot trigger log exists with timestamp and reason
- ✅ All services auto-start after reboot

---

## Test 4: Power Loss (auto-start on boot)

**Expected**: All services start automatically after power cycle

```bash
# Method 1: Clean reboot
sudo reboot

# Method 2: Actual power cycle (unplug/replug)
# (Physically unplug the Raspberry Pi, wait 10 seconds, plug back in)
```

**After reboot (wait 2 minutes for boot):**

```bash
# SSH back in
ssh philip@raspberrypi.local  # or use IP address

# Check all services are running
sudo systemctl status recorder.service
sudo systemctl status recorder-watchdog.service
sudo systemctl status recorder-metrics.service

# All should show "active (running)"

# Check heartbeat
cat /tmp/recorder_heartbeat.json

# Check metrics
curl http://localhost:9101/metrics | head -20
```

**Success criteria:**
- ✅ All 3 services auto-start on boot
- ✅ Heartbeat file exists and is fresh
- ✅ Metrics endpoint responds
- ✅ Green LED is on (system ready)

---

## Test 5: Disk Full Condition

**Expected**: Service refuses to record, shows red LED

```bash
# Create a large file to fill disk (adjust size as needed)
dd if=/dev/zero of=/opt/raspberry-pi-video-recorder/temp_videos/filler.bin bs=1M count=5000

# Try to start a recording (press button)
# Expected: Red LED, no recording

# Check logs
tail -f /var/log/recorder/service.log
# Should see: "Insufficient storage space!"

# Cleanup
rm /opt/raspberry-pi-video-recorder/temp_videos/filler.bin

# Press button to attempt recovery
# Expected: Green LED returns
```

**Success criteria:**
- ✅ Service detects disk full condition
- ✅ Red LED displays
- ✅ Service refuses to record
- ✅ After cleanup, service recovers to ready state

---

## Test 6: Network Disconnect

**Expected**: White LED turns off, uploads pause but recordings continue

```bash
# Disconnect WiFi/Ethernet
sudo ifconfig wlan0 down  # For WiFi
# OR
sudo ifconfig eth0 down   # For Ethernet

# Observe white LED turns off (no internet)

# Try recording - should still work
# Press button, recording starts (green LED blinks)

# Reconnect network
sudo ifconfig wlan0 up    # For WiFi
# OR
sudo ifconfig eth0 up     # For Ethernet

# White LED should turn back on
```

**Success criteria:**
- ✅ White LED indicates network status
- ✅ Recording works without network
- ✅ Uploads resume when network returns
- ✅ Blue LED blinks during uploads

---

## Monitoring Commands

### View Live Logs

```bash
# Recorder service logs
sudo journalctl -u recorder.service -f

# Watchdog logs
tail -f /var/log/recorder/watchdog.log

# All recorder logs
tail -f /var/log/recorder/service.log

# Metrics logs
sudo journalctl -u recorder-metrics.service -f
```

### Check Service Status

```bash
# Quick status of all services
sudo systemctl status recorder.service recorder-watchdog.service recorder-metrics.service

# Check if auto-start is enabled
sudo systemctl is-enabled recorder.service
sudo systemctl is-enabled recorder-watchdog.service
sudo systemctl is-enabled recorder-metrics.service
```

### Check Heartbeat

```bash
# View current heartbeat
cat /tmp/recorder_heartbeat.json

# Watch heartbeat update in real-time
watch -n 1 cat /tmp/recorder_heartbeat.json
```

### Check Metrics

```bash
# Fetch current metrics
curl http://localhost:9101/metrics

# Watch specific metric
watch -n 1 'curl -s http://localhost:9101/metrics | grep recorder_up'
```

---

## Success Criteria Summary

After completing all tests, you should have verified:

- ✅ Service auto-restarts on crash (systemd)
- ✅ Service auto-restarts on freeze (watchdog)
- ✅ System reboots if service unrecoverable (watchdog)
- ✅ All services auto-start on boot
- ✅ Disk full detection works
- ✅ Network status monitoring works
- ✅ Heartbeat updates every second
- ✅ Metrics endpoint responds
- ✅ All logs are being written

**Congratulations! Your auto-recovery system is production-ready!** 🎉
