# Raspberry Pi 5 - Quick Setup Checklist

**Print this and keep it handy for new installations!**

---

## ⚡ 5-Minute Setup

```bash
# 1. Install GPIO libraries (Pi 5 specific)
sudo apt-get update
sudo apt-get install -y python3-lgpio python3-rpi-lgpio ffmpeg

# 2. Fix permissions
sudo usermod -a -G gpio $(whoami)

# 3. Create virtual environment (WITH system packages!)
cd /opt/raspberry-pi-video-recorder
python3 -m venv .venv --system-site-packages

# 4. Install dependencies
source .venv/bin/activate
pip install -r requirements.txt

# 5. Reboot (required for gpio group)
sudo reboot
```

---

## 🔧 Hardware Wiring

### GPIO Pin Configuration
```
Button:      GPIO 18 (pin 12) + GND (pin 14)
LED Green:   GPIO 13 (pin 33) + GND (pin 34)
LED Orange:  GPIO 12 (pin 32) + GND (pin 30)
LED Red:     GPIO 19 (pin 35) + GND (pin 39)
```

**All LEDs use hardware PWM pins for consistent brightness!**

---

## ✅ Verification Tests

```bash
# Test GPIO import
python -c "import RPi.GPIO; print('✓ GPIO OK')"

# Test LEDs
python test_led.py

# Test button
python test_button.py

# Test camera
v4l2-ctl --list-devices

# Run service
python recorder_service.py
```

---

## 🚨 Common Issues

| Problem | Solution |
|---------|----------|
| `Cannot determine SOC peripheral base address` | Install `python3-rpi-lgpio` and recreate venv with `--system-site-packages` |
| `Permission denied` on GPIO | Add user to gpio group: `sudo usermod -a -G gpio $(whoami)` then reboot |
| `ModuleNotFoundError: RPi` in venv | Recreate venv: `rm -rf .venv && python3 -m venv .venv --system-site-packages` |
| Need sudo for GPIO | Reboot after adding to gpio group |
| LEDs different brightness | Check using hardware PWM pins (12, 13, 19) |

---

## 📋 Pre-Install Checklist

- [ ] Raspberry Pi 5 (or check model with `cat /proc/cpuinfo | grep Model`)
- [ ] Fresh Raspberry Pi OS install
- [ ] Internet connection
- [ ] Camera connected and detected (`ls /dev/video*`)
- [ ] YouTube API credentials ready
- [ ] 3x LEDs with built-in resistors (panel mount)
- [ ] 1x momentary push button
- [ ] Jumper wires

---

## 🎯 The Two Critical Pi 5 Requirements

### 1. GPIO Library: Use `rpi-lgpio`, not `RPi.GPIO`
```bash
sudo apt-get install python3-rpi-lgpio
```

### 2. Virtual Environment: MUST use `--system-site-packages`
```bash
python3 -m venv .venv --system-site-packages
                      ^^^^^^^^^^^^^^^^^^^^^^^^
                      DON'T FORGET THIS FLAG!
```

**Why?** Pi 5's GPIO chip (RP1) requires system packages that can't be pip installed easily.

---

## 🔄 Quick Reinstall

If something goes wrong, start fresh:

```bash
rm -rf .venv
python3 -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 📖 Full Documentation

- **Complete guide:** `INSTALL.md`
- **Troubleshooting:** `INSTALL.md#troubleshooting`
- **Automated setup:** Run `./setup_pi5.sh`
