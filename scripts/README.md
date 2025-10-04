# Hardware Test Scripts

Real hardware validation scripts for the Raspberry Pi video recording system.

## Purpose

These scripts test hardware components with **actual devices** (real GPIO, real TTS, etc.), unlike the unit tests in `tests/` which use mocks. Run these before deploying to verify hardware is working correctly.

## Quick Start

```bash
# Test audio on your computer
python scripts/test_audio.py

# On Raspberry Pi, test everything
python scripts/test_all_hardware.py
```

## Scripts Overview

### `test_audio.py` - Audio/TTS Testing
**Run on:** Computer or Raspberry Pi
**Hardware needed:** Speakers/headphones

Tests text-to-speech audio output through real speakers.

**What it tests:**
- TTS engine initialization
- Playing predefined system messages
- Playing custom text
- Volume control
- Speech rate adjustment
- Message queue (sequential playback)

**Expected output:**
You should hear several voice messages play through your speakers, including:
- "Audio test successful"
- "System ready"
- "Recording started"
- Various other system messages

**Run time:** ~30 seconds

---

### `test_leds.py` - LED Status Display Testing
**Run on:** Raspberry Pi only
**Hardware needed:** 3 LEDs connected to GPIO pins 12, 16, 20

Tests LED control through GPIO pins.

**What it tests:**
- Individual LED patterns (green, orange, red)
- Blinking behavior (recording state)
- Error flash (rapid red blink)
- Pattern transitions
- Full recording sequence simulation

**Expected output:**
Watch the LEDs:
1. Green LED lights up (READY)
2. Orange LED lights up (PROCESSING)
3. Red LED lights up (ERROR)
4. Green LED blinks (RECORDING)
5. All LEDs turn off

**Run time:** ~30 seconds

---

### `test_button.py` - Button Input Testing
**Run on:** Raspberry Pi only
**Hardware needed:** Push button connected to GPIO pin 18

Tests button press detection with debouncing and double-tap logic.

**What it tests:**
- Single press detection
- Double press detection (two quick presses)
- Timing window configuration
- Interrupt-based input handling

**Expected output:**
Press the button and see:
```
[12:34:56] SINGLE press detected (total: 1)
[12:34:58] DOUBLE press detected (total: 1)
```

**Run time:** 25 seconds (interactive)

**Interaction required:** You must press the button during the test

---

### `test_all_hardware.py` - Comprehensive Test Suite
**Run on:** Raspberry Pi (recommended) or Computer (audio only)
**Hardware needed:** All components

Runs all hardware tests in sequence and provides a pass/fail summary.

**What it tests:**
- Audio system (3 messages)
- LED system (all patterns)
- Button system (10-second test window)

**Expected output:**
```
======================================================================
                     HARDWARE SMOKE TEST SUITE
======================================================================

Checking hardware availability...
  GPIO: Available
  TTS:  Available

----------------------------------------------------------------------
TESTING: Audio System
----------------------------------------------------------------------
...
[PASS] Audio System

----------------------------------------------------------------------
TESTING: LED System
----------------------------------------------------------------------
...
[PASS] LED System

----------------------------------------------------------------------
TESTING: Button System
----------------------------------------------------------------------
...
[PASS] Button System

======================================================================
                         TEST SUMMARY
======================================================================

Tests Passed: 3/3

PASSED:
  - Audio System
  - LED System
  - Button System

All hardware tests passed!
System is ready for deployment.
```

**Run time:** ~60 seconds

---

## When to Run These Tests

**Before each deployment:**
Run `test_all_hardware.py` on the Raspberry Pi to verify everything works.

**After hardware changes:**
- Rewired LEDs → Run `test_leds.py`
- Changed button → Run `test_button.py`
- Updated TTS settings → Run `test_audio.py`

**During development:**
Run individual tests to verify changes to specific controllers.

**After code changes:**
Always run both:
1. Unit tests: `pytest tests/hardware/` (fast, uses mocks)
2. Hardware tests: `python scripts/test_all_hardware.py` (real hardware)

---

## Running on Different Systems

### On Your Development Computer
```bash
# Only audio will work (no GPIO)
python scripts/test_audio.py
```

Scripts will detect you're not on a Pi and use simulation mode for GPIO.

### On Raspberry Pi
```bash
# Test everything
python scripts/test_all_hardware.py

# Or test individually
python scripts/test_audio.py
python scripts/test_leds.py
python scripts/test_button.py
```

---

## Exit Codes

All scripts return proper exit codes for scripting:
- `0` = All tests passed
- `1` = Test failed or error occurred

Use in deployment scripts:
```bash
python scripts/test_all_hardware.py && echo "Deploy!" || echo "Fix hardware first"
```

---

## Troubleshooting

### Audio Test Issues

**Problem:** No sound heard
**Solutions:**
- Check speakers are connected and not muted
- Verify pyttsx3 is installed: `pip install pyttsx3`
- On Linux, ensure audio drivers are working: `speaker-test -t wav -c 2`

**Problem:** "TTS not available" error
**Solutions:**
- Install pyttsx3: `pip install pyttsx3`
- On Linux, install espeak: `sudo apt-get install espeak`
- Check Python version (3.8+)

### LED Test Issues

**Problem:** LEDs don't light up
**Solutions:**
- Verify running on Raspberry Pi
- Check GPIO wiring (pins 12, 16, 20)
- Test with multimeter (should see ~3.3V when ON)
- Check LED polarity (long leg = positive)
- Verify current-limiting resistors (220Ω-1kΩ)

**Problem:** "GPIO not available" error
**Solutions:**
- Install RPi.GPIO: `pip install RPi.GPIO`
- Run with sudo if permission denied: `sudo python scripts/test_leds.py`
- Check `/dev/gpiomem` permissions

### Button Test Issues

**Problem:** No button presses detected
**Solutions:**
- Check button wiring (GPIO 18 to button, other side to GND)
- Verify button is not stuck
- Test button continuity with multimeter
- Try pressing button multiple times firmly

**Problem:** False triggers / bouncing
**Solutions:**
- Add hardware debouncing (0.1µF capacitor across button)
- Adjust debounce time in code: `button.set_timing(debounce_time=0.1)`

### General Issues

**Problem:** Import errors
**Solution:** Ensure you're in project root directory when running scripts

**Problem:** Scripts hang
**Solution:** Press Ctrl+C to interrupt, check for hardware connection issues

---

## Hardware Requirements

### GPIO Pin Assignments
- **Button:** GPIO 18 (with pull-up resistor, press connects to GND)
- **LED Green:** GPIO 12 (with current-limiting resistor)
- **LED Orange:** GPIO 16 (with current-limiting resistor)
- **LED Red:** GPIO 20 (with current-limiting resistor)

### Wiring Diagram Reference
See `docs/hardware_wiring.md` for detailed wiring diagrams (if available).

---

## Integration with Unit Tests

These scripts complement but don't replace unit tests:

| Type | Location | Use Case | Speed | Hardware |
|------|----------|----------|-------|----------|
| Unit Tests | `tests/hardware/` | Development, CI/CD | Fast (seconds) | Mock |
| Hardware Tests | `scripts/` | Pre-deployment | Slow (minutes) | Real |

**Workflow:**
1. Write code
2. Run unit tests: `pytest tests/hardware/` (fast feedback)
3. Deploy to Pi
4. Run hardware tests: `python scripts/test_all_hardware.py` (validate)
5. Deploy to production

---

## Customization

### Adjusting Test Duration

Edit timing in scripts:
```python
# In test_leds.py
time.sleep(2)  # Change LED display time

# In test_button.py
test_duration = 15  # Change button test duration
```

### Adding Custom Tests

Create new scripts following the pattern:
```python
#!/usr/bin/env python3
from hardware.factory import HardwareFactory

def test_my_hardware():
    # Initialize hardware
    # Run tests
    # Print results
    pass

if __name__ == "__main__":
    test_my_hardware()
```

---

## Pre-Deployment Checklist

Before deploying to production:

- [ ] Unit tests pass: `pytest tests/hardware/ -v`
- [ ] Audio test passes: `python scripts/test_audio.py`
- [ ] LED test passes: `python scripts/test_leds.py`
- [ ] Button test passes: `python scripts/test_button.py`
- [ ] All hardware test passes: `python scripts/test_all_hardware.py`
- [ ] System integration test (record test video)

---

## Support

For issues with these scripts:
1. Check troubleshooting section above
2. Verify hardware connections
3. Check logs for error messages
4. Test hardware with simple GPIO examples first
