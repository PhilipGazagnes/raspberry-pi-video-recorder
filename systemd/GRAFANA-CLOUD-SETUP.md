# Grafana Cloud Setup Guide

Complete guide for setting up Grafana Cloud (free tier) for remote monitoring.

**Cost:** €0/month (Free Forever plan)
**Limits:** 10k metrics series, 50GB logs/month, 14-day retention
**Perfect for:** 1-10 devices

---

## Step 1: Create Grafana Cloud Account

### 1.1 Sign Up

Go to: https://grafana.com/auth/sign-up/create-user

**Fill in:**
- Email address
- Username
- Password
- Organization name (e.g., "My Recorder")

**Choose plan:** Free Forever ✅

Click **"Create Account"**

### 1.2 Verify Email

Check your email for verification link and click it.

---

## Step 2: Get Connection Details

After logging in, you'll be in your Grafana Cloud dashboard.

### 2.1 Get Prometheus (Metrics) Credentials

1. Click **"Send Metrics"** or navigate to **Connections > Add new connection**
2. Choose **"Prometheus"** as the data source
3. You'll see connection details:

```
Remote Write Endpoint:
https://prometheus-prod-XX-prod-XX-XX.grafana.net/api/prom/push

Username: XXXXXX
Password: glc_eyJrIjoiXXXXXXXXXXXXXXXXXX...
```

**Save these!** You'll need them for Grafana Agent configuration.

### 2.2 Get Loki (Logs) Credentials

1. Click **"Send Logs"** or navigate to **Connections > Add new connection**
2. Choose **"Loki"** as the data source
3. You'll see connection details:

```
Loki Endpoint:
https://logs-prod-XX.grafana.net/loki/api/v1/push

Username: XXXXXX
Password: glc_eyJrIjoiXXXXXXXXXXXXXXXXXX...
```

**Save these too!**

---

## Step 3: Save Credentials Securely

Create a credentials file on your Raspberry Pi:

```bash
cd /opt/raspberry-pi-video-recorder

# Create credentials directory
mkdir -p credentials/grafana

# Create credentials file (KEEP THIS SECURE!)
nano credentials/grafana/cloud-credentials.txt
```

**Paste this template and fill in your values:**

```
# Grafana Cloud Credentials
# KEEP THIS FILE SECURE - DO NOT COMMIT TO GIT

# Prometheus (Metrics)
PROMETHEUS_URL=https://prometheus-prod-XX-prod-XX-XX.grafana.net/api/prom/push
PROMETHEUS_USERNAME=XXXXXX
PROMETHEUS_PASSWORD=glc_eyJrIjoiXXXXXXXXXXXXXXXXXX...

# Loki (Logs)
LOKI_URL=https://logs-prod-XX.grafana.net/loki/api/v1/push
LOKI_USERNAME=XXXXXX
LOKI_PASSWORD=glc_eyJrIjoiXXXXXXXXXXXXXXXXXX...

# Instance Label (identifies this device)
INSTANCE_LABEL=balaruc-les-bains-gym
CUSTOMER_LABEL=balaruc-les-bains
LOCATION_LABEL=gym
```

**Save and exit** (Ctrl+X, Y, Enter)

**Set secure permissions:**
```bash
chmod 600 credentials/grafana/cloud-credentials.txt
```

---

## Step 4: Verify Access

Test that your credentials work:

### Test Prometheus

```bash
# Load credentials
source credentials/grafana/cloud-credentials.txt

# Test with a dummy metric
curl -u "$PROMETHEUS_USERNAME:$PROMETHEUS_PASSWORD" \
  -X POST "$PROMETHEUS_URL" \
  -H "Content-Type: application/x-protobuf" \
  -H "X-Prometheus-Remote-Write-Version: 0.1.0" \
  --data-binary @- <<EOF
# Empty test - just verify authentication works
EOF
```

**Expected:** HTTP 204 or 400 (both mean auth worked, 400 is empty data)
**Problem:** HTTP 401 = wrong credentials

### Test Loki

```bash
# Test Loki endpoint
curl -u "$LOKI_USERNAME:$LOKI_PASSWORD" \
  "$LOKI_URL" \
  -X POST \
  -H "Content-Type: application/json" \
  --data-raw '{
    "streams": [{
      "stream": {"job": "test"},
      "values": [["'"$(date +%s)"'000000000", "test message"]]
    }]
  }'
```

**Expected:** HTTP 204 (success) or similar
**Problem:** HTTP 401 = wrong credentials

---

## Step 5: Add to .gitignore

**IMPORTANT:** Never commit credentials to git!

```bash
# Add to .gitignore
echo "credentials/grafana/" >> .gitignore
```

---

## Credentials Summary

You now have:

✅ Grafana Cloud account (free tier)
✅ Prometheus URL and credentials (for metrics)
✅ Loki URL and credentials (for logs)
✅ Credentials saved securely on Pi
✅ Ready for Grafana Agent installation

---

## Next Step

**Task 2.3:** Install Grafana Agent

The Grafana Agent will use these credentials to ship your metrics and logs to Grafana Cloud.

Run:
```bash
./systemd/install-grafana-agent.sh
```

This script will:
1. Read your credentials from `credentials/grafana/cloud-credentials.txt`
2. Install Grafana Agent
3. Configure it to send metrics + logs to Grafana Cloud
4. Start the service

---

## Troubleshooting

### Can't find connection details

1. Log into https://grafana.com
2. Click your organization name (top left)
3. Go to **"Connections"** in left sidebar
4. Click **"Add new connection"**
5. Search for "Prometheus" or "Loki"

### Forgot credentials

You can regenerate API keys:
1. Go to **"Security" > "API Keys"** in Grafana Cloud
2. Create new API key
3. Update your credentials file

### Free tier limits

**Metrics:** 10,000 active series
- Your setup uses ~50 series (plenty of room!)

**Logs:** 50GB/month
- Your logs are tiny (~1MB/day = 30MB/month)

**Retention:** 14 days
- Logs and metrics deleted after 2 weeks
- Upgrade to Pro for longer retention

---

## Support

**Grafana Cloud docs:** https://grafana.com/docs/grafana-cloud/
**Support:** Help > Support in Grafana Cloud dashboard

---

**Ready for next step?** Continue to Task 2.3: Install Grafana Agent
