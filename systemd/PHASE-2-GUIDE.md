# Phase 2: Visual Monitoring (Grafana Cloud)

Complete installation guide for remote monitoring with Grafana Cloud.

**Result:** Monitor your recorder from anywhere - phone, laptop, etc.
**Cost:** €0/month (free tier)
**Time:** ~1-2 hours

---

## Overview

**What you'll get:**
- 📊 Beautiful dashboards showing CPU, RAM, disk, recordings, uploads
- 📱 Monitor from your phone/laptop anywhere in the world
- 🚨 Email alerts when issues occur
- 📝 Live logs from your device
- 📈 14-day history of all metrics

**Architecture:**
```
Raspberry Pi
├─ Node Exporter (port 9100) → System metrics (CPU, RAM, disk, temp)
├─ Recorder Metrics (port 9101) → App metrics (state, uploads, etc)
├─ Log files (/var/log/recorder/) → Service logs
└─ Grafana Agent → Ships everything to Grafana Cloud
                                    ↓
                          Grafana Cloud (FREE)
                          ├─ Dashboards
                          ├─ Alerts
                          └─ Logs
```

---

## Installation Steps

### Task 2.1: Install Node Exporter ✅

**What it does:** Exports system metrics (CPU, RAM, disk, temperature)

```bash
cd /opt/raspberry-pi-video-recorder
./systemd/install-node-exporter.sh
```

**Verify:**
```bash
curl http://localhost:9100/metrics | head -20
```

Should see metrics like `node_cpu_seconds_total`, `node_memory_MemAvailable_bytes`, etc.

---

### Task 2.2: Setup Grafana Cloud ✅

**What it does:** Creates your free cloud monitoring account

**Follow:** `systemd/GRAFANA-CLOUD-SETUP.md`

**Summary:**
1. Sign up at https://grafana.com (Free Forever plan)
2. Get Prometheus credentials (metrics)
3. Get Loki credentials (logs)
4. Save credentials to `credentials/grafana/cloud-credentials.txt`

**Verify:**
```bash
# Check credentials file exists
cat credentials/grafana/cloud-credentials.txt
```

---

### Task 2.3: Install Grafana Agent ✅

**What it does:** Ships your metrics and logs to Grafana Cloud

```bash
./systemd/install-grafana-agent.sh
```

**Verify:**
```bash
sudo systemctl status grafana-agent.service
# Should show "active (running)"

# Check logs
sudo journalctl -u grafana-agent.service -n 20
# Should NOT show authentication errors
```

**Wait 2 minutes** for first data to arrive in Grafana Cloud.

---

### Task 2.4: Create Dashboards 📊

**What it does:** Visualizes your metrics in beautiful graphs

#### 2.4.1: Import Node Exporter Dashboard

1. **Log into Grafana Cloud**: https://grafana.com
2. Click **Dashboards** (left sidebar)
3. Click **"New"** → **"Import"**
4. Enter dashboard ID: **`1860`**
5. Click **"Load"**
6. Select your Prometheus data source
7. Click **"Import"**

**Result:** Beautiful system metrics dashboard! 🎉

Shows: CPU usage, RAM, disk space, network, temperature, load average

#### 2.4.2: Create Custom Recorder Dashboard

1. Click **Dashboards** → **"New"** → **"New Dashboard"**
2. Click **"Add visualization"**
3. Select your Prometheus data source

**Add these panels:**

**Panel 1: Service Status (Stat)**
- Query: `recorder_up`
- Title: "Service Status"
- Thresholds:
  - 0 = Red (Down)
  - 1 = Green (Up)

**Panel 2: Current State (Stat)**
- Query: `recorder_state`
- Title: "Current State"
- Value mappings:
  - 1 = "Ready" (Green)
  - 2 = "Recording" (Blue)
  - 3 = "Error" (Red)

**Panel 3: Disk Free (Gauge)**
- Query: `recorder_disk_free_bytes / 1024 / 1024 / 1024`
- Title: "Disk Free (GB)"
- Unit: "GB"
- Thresholds:
  - <5 = Red
  - <10 = Yellow
  - >=10 = Green

**Panel 4: Upload Success Rate (Gauge)**
- Query: `recorder_upload_success_rate * 100`
- Title: "Upload Success Rate"
- Unit: "%"
- Thresholds:
  - <90 = Red
  - <95 = Yellow
  - >=95 = Green

**Panel 5: Videos by Status (Pie Chart)**
- Queries:
  - `recorder_videos_total{status="pending"}`
  - `recorder_videos_total{status="completed"}`
  - `recorder_videos_total{status="failed"}`
  - `recorder_videos_total{status="corrupted"}`
- Title: "Videos by Status"

**Panel 6: CPU Temperature (Time Series)**
- Query: `node_hwmon_temp_celsius`
- Title: "CPU Temperature"
- Unit: "°C"
- Threshold line at 80°C (warning)

**Panel 7: Memory Usage (Time Series)**
- Query: `100 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100)`
- Title: "Memory Usage (%)"
- Unit: "%"

**Panel 8: Recordings per Day (Time Series)**
- Query: `increase(recorder_videos_total{status="completed"}[24h])`
- Title: "Recordings (Last 24h)"

4. **Arrange panels** in a nice layout
5. Click **"Save dashboard"**
6. Name it: **"Recorder - [Your Location]"**

---

### Task 2.5: Setup Alerts 🚨

**What it does:** Sends email when problems occur

#### 2.5.1: Configure Contact Point

1. Go to **"Alerting"** → **"Contact points"**
2. Click **"New contact point"**
3. Name: **"Email Notifications"**
4. Type: **"Email"**
5. Addresses: **your-email@example.com**
6. Click **"Test"** to verify
7. Click **"Save contact point"**

#### 2.5.2: Create Alert Rules

**Alert 1: Service Down (CRITICAL)**
1. Go to **"Alerting"** → **"Alert rules"**
2. Click **"New alert rule"**
3. Name: **"Service Down"**
4. Query:
   - A: `recorder_up`
   - Condition: `A < 1`
5. Evaluate: **For 1 minute**
6. Folder: **"Recorder Alerts"**
7. Contact point: **"Email Notifications"**
8. Summary: **"🔴 Recorder service is DOWN at {{instance}}"**
9. Click **"Save"**

**Alert 2: Disk Space Low (WARNING)**
1. New alert rule
2. Name: **"Disk Space Low"**
3. Query:
   - A: `recorder_disk_free_bytes`
   - Condition: `A < 5000000000` (5GB)
4. Evaluate: **For 5 minutes**
5. Contact point: **"Email Notifications"**
6. Summary: **"⚠️ Low disk space at {{instance}}"**
7. Save

**Alert 3: Upload Success Rate Low (WARNING)**
1. New alert rule
2. Name: **"Upload Success Rate Low"**
3. Query:
   - A: `recorder_upload_success_rate`
   - Condition: `A < 0.95` (95%)
4. Evaluate: **For 1 hour**
5. Contact point: **"Email Notifications"**
6. Summary: **"⚠️ Upload success rate below 95% at {{instance}}"**
7. Save

**Alert 4: High Temperature (WARNING)**
1. New alert rule
2. Name: **"High Temperature"**
3. Query:
   - A: `node_hwmon_temp_celsius`
   - Condition: `A > 80`
4. Evaluate: **For 5 minutes**
5. Contact point: **"Email Notifications"**
6. Summary: **"🌡️ High temperature (>80°C) at {{instance}}"**
7. Save

---

## Verification

### Check Metrics Arriving

**In Grafana Cloud:**
1. Go to **"Explore"**
2. Select Prometheus data source
3. Query: `recorder_up`
4. Should see: `1` (service is up)

### Check Logs Arriving

**In Grafana Cloud:**
1. Go to **"Explore"**
2. Select Loki data source
3. Query: `{job="recorder-service"}`
4. Should see logs from your recorder service

### Test Alerts

**Trigger test alert:**
```bash
# On Raspberry Pi, stop the service
sudo systemctl stop recorder.service

# Wait 2 minutes
# You should receive email: "Service Down"

# Restart service
sudo systemctl start recorder.service

# Wait 1 minute
# You should receive email: "Service Recovered"
```

---

## Mobile Access

### Grafana Mobile App

**iOS/Android:**
1. Download **"Grafana"** app from App Store/Play Store
2. Log in with your Grafana Cloud account
3. View dashboards on your phone!

**Result:** Check system status from anywhere 📱

---

## Costs & Limits

**Free Forever Plan:**
- ✅ 10,000 active metrics series (you use ~50)
- ✅ 50GB logs per month (you use ~30MB)
- ✅ 14-day retention
- ✅ Unlimited dashboards
- ✅ Unlimited alerts
- ✅ Email notifications

**Upgrade (if needed):**
- **Pro**: $8/month - 1 million metrics, 100GB logs, 30-day retention
- **Advanced**: $299/month - For large deployments

**You're fine with Free tier for 1-10 devices!**

---

## Troubleshooting

### No metrics in Grafana Cloud

**Check Grafana Agent:**
```bash
sudo systemctl status grafana-agent.service
sudo journalctl -u grafana-agent.service -n 50
```

**Look for:**
- ❌ Authentication errors → wrong credentials
- ❌ Connection refused → firewall blocking
- ✅ "remote_write" success messages → working!

**Fix wrong credentials:**
1. Update `credentials/grafana/cloud-credentials.txt`
2. Regenerate config: `./systemd/install-grafana-agent.sh`
3. Restart: `sudo systemctl restart grafana-agent.service`

### No logs in Grafana Cloud

**Check log files exist:**
```bash
ls -la /var/log/recorder/
# Should show service.log, watchdog.log
```

**Check Grafana Agent has read permission:**
```bash
sudo chmod 644 /var/log/recorder/*.log
sudo systemctl restart grafana-agent.service
```

### Alerts not sending

**Check contact point:**
1. Go to **"Alerting" → "Contact points"**
2. Click **"Test"** on your email contact point
3. Check spam folder for test email

**Check alert rules:**
1. Go to **"Alerting" → "Alert rules"**
2. Check rule status (should be "Normal" or "Firing")

---

## What's Next?

**You now have:**
- ✅ Remote monitoring from anywhere
- ✅ Beautiful dashboards
- ✅ Email alerts
- ✅ Live logs
- ✅ System health visibility

**Optional enhancements:**
- Add more custom panels to dashboards
- Create Slack/Discord notifications (instead of email)
- Set up SMS alerts (requires paid tier)
- Create weekly summary reports
- Monitor multiple devices in one dashboard

---

## Phase 2 Complete! 🎉

Your recorder now has **professional-grade monitoring**!

**Before Phase 2:**
- ✅ Service auto-recovers
- ✅ Logs written locally
- ❌ No remote visibility

**After Phase 2:**
- ✅ Service auto-recovers
- ✅ Logs written locally AND shipped to cloud
- ✅ Monitor from phone anywhere
- ✅ Email alerts when issues occur
- ✅ Historical graphs and trends

---

**Next:** Phase 3 - Professional Tools (optional)
- Quick status script
- Recovery documentation
- Advanced testing

See `PEACE_OF_MIND.md` for details.
