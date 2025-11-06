# Installation Guide - Raspberry Pi Video Recorder

## Prerequisites

- Raspberry Pi (tested on Pi 5)
- Raspberry Pi OS (Bookworm or later)
- USB camera or Pi Camera Module
- Internet connection for uploads

---

## Quick Install (Raspberry Pi 5)

If you're on **Raspberry Pi 5**, use the automated setup script:

```bash
cd /opt/raspberry-pi-video-recorder
chmod +x setup_pi5.sh
./setup_pi5.sh
```

This handles all the Pi 5-specific requirements. After it completes, **reboot** and skip to [Testing](#testing).

---

## Manual Installation

### 1. System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y ffmpeg v4l-utils python3-pip python3-venv
```

### 2. GPIO Libraries

**⚠️ IMPORTANT: Raspberry Pi 5 vs older models**

<details>
<summary><strong>Raspberry Pi 5</strong> (RP1 GPIO chip)</summary>

Pi 5 requires `lgpio` instead of `RPi.GPIO`:

```bash
# Install GPIO libraries from system packages
sudo apt-get install -y python3-lgpio python3-rpi-lgpio
```

**Why system packages?** The `lgpio` library needs to be compiled, and system packages are pre-built and more reliable.

</details>

<details>
<summary><strong>Raspberry Pi 4 and older</strong> (BCM GPIO)</summary>

```bash
# RPi.GPIO works fine on older models
sudo apt-get install -y python3-rpi.gpio
```

</details>

### 3. GPIO Permissions

Add your user to the `gpio` group to access GPIO without `sudo`:

```bash
# Add current user to gpio group
sudo usermod -a -G gpio $(whoami)

# Verify it worked
groups $(whoami)  # Should show 'gpio' in the list

# Log out and back in (or reboot) for this to take effect
sudo reboot
```

**Why this matters:** Without this, you'll need to run the service with `sudo`, which causes virtual environment issues.

### 4. Python Virtual Environment

**⚠️ CRITICAL for Raspberry Pi 5:**

Create venv **with system site packages** to access GPIO libraries:

```bash
cd /opt/raspberry-pi-video-recorder

# Create venv with --system-site-packages flag
python3 -m venv .venv --system-site-packages

# Activate it
source .venv/bin/activate

# Verify GPIO works
python -c "import RPi.GPIO; print('GPIO OK')"
```

**Common mistake:** Forgetting `--system-site-packages` flag. Without it, GPIO libraries won't be accessible.

### 5. Python Dependencies

```bash
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-upload.txt  # YouTube upload dependencies
```

### 6. YouTube Authentication (Optional)

⚠️ **Requires a browser** - do this step from the Pi with a display, or via VNC/remote desktop.

```bash
# Ensure credentials directory exists
mkdir -p credentials

# Place your client_secret.json file (from Google Cloud Console)
# in credentials/client_secret.json

# Run authentication script (opens browser)
source .venv/bin/activate
python setup_youtube_auth.py
```

This creates `credentials/token.json` which is used for automatic uploads.

**Skip this step if:** You want to test the system without YouTube uploads first (it will use mock uploader).

---

### 7. Configure Logging (Automatic in setup script)

The service logs to `/var/log/recorder-service.log` by default.

**Automatic setup** (if you used `setup_pi5.sh`):
- Log file already created with proper permissions ✓

**Manual setup** (if you skipped the script):
```bash
# Create log file with proper permissions
sudo touch /var/log/recorder-service.log
sudo chown $(whoami):$(whoami) /var/log/recorder-service.log
sudo chmod 664 /var/log/recorder-service.log
```

**Fallback behavior:**
If `/var/log/` is not writable, logs automatically write to `logs/recorder-service.log` in the project directory.

---

## Testing

### Test GPIO Hardware

```bash
source .venv/bin/activate

# Test LEDs
sudo python test_led.py

# Test button
sudo python test_button.py
```

**Note:** You need `sudo` for the test scripts even after adding yourself to the gpio group, because the gpio group membership only takes effect after logout/reboot.

### Test Camera

```bash
# List available cameras
v4l2-ctl --list-devices

# Test camera capture
ffmpeg -f v4l2 -i /dev/video0 -frames 1 test.jpg
```

### Run the Service

```bash
source .venv/bin/activate
python recorder_service.py
```

You should see:
```
System READY for recording
```

Press the button to start/stop recording!

---

## Troubleshooting

### "Cannot determine SOC peripheral base address"

**Problem:** Running on Pi 5 but using wrong GPIO library

**Solution:**
1. Install `python3-rpi-lgpio` system package
2. Recreate venv with `--system-site-packages`

```bash
sudo apt-get install python3-rpi-lgpio
rm -rf .venv
python3 -m venv .venv --system-site-packages
```

### "Permission denied" on GPIO

**Problem:** User not in `gpio` group

**Solution:**
```bash
sudo usermod -a -G gpio $(whoami)
sudo reboot
```

### GPIO imports work with sudo but not without

**Problem:** venv doesn't have access to system GPIO packages

**Solution:** Recreate venv with `--system-site-packages`:
```bash
rm -rf .venv
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
```

### LEDs have different brightness

**Problem:** Using mixed GPIO pin types (hardware PWM vs regular GPIO)

**Solution:** Use consistent pin types. Current config uses all hardware PWM pins (12, 13, 19) for even brightness.

### "Module not found" errors when using sudo

**Problem:** `sudo python` uses system Python, not venv

**Solution:** Use venv's Python with sudo:
```bash
sudo .venv/bin/python recorder_service.py
```

Or better: Fix gpio group membership to avoid needing sudo.

---

## Raspberry Pi 5 Quick Reference

**TL;DR for Pi 5:**
1. Install `python3-rpi-lgpio` system package
2. Add user to `gpio` group
3. Create venv with `--system-site-packages`
4. Reboot

```bash
sudo apt-get install -y python3-rpi-lgpio
sudo usermod -a -G gpio $(whoami)
python3 -m venv .venv --system-site-packages
sudo reboot
```

---

## Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- Setting up as systemd service
- Auto-start on boot
- Log management
- Network configuration
