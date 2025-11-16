#!/usr/bin/env python3
"""
Test if camera supports audio capture.

This script checks:
1. If the camera device exists
2. If FFmpeg can detect audio from the camera
3. What audio formats are available

Usage:
    python scripts/test_camera_audio.py
"""

import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import DEFAULT_CAMERA_DEVICE


def check_camera_audio_support(camera_device: str = DEFAULT_CAMERA_DEVICE) -> None:
    """
    Test if camera device supports audio capture.

    Args:
        camera_device: Path to camera device (e.g., /dev/video0)
    """
    print(f"Testing camera audio support: {camera_device}\n")
    print("=" * 60)

    # Test 1: Check if device exists
    print("\n1. Checking if camera device exists...")
    if not Path(camera_device).exists():
        print(f"   ❌ Camera device not found: {camera_device}")
        print("\n   Run 'ls /dev/video*' to see available cameras")
        return
    print(f"   ✓ Camera device exists: {camera_device}")

    # Test 2: List all audio devices
    print("\n2. Checking available audio devices...")
    print("   Running: ffmpeg -sources pulse")
    try:
        result = subprocess.run(
            ["ffmpeg", "-sources", "pulse"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        if result.returncode == 0:
            print("   Available audio sources:")
            print(result.stdout)
        else:
            # Try ALSA instead
            print("   PulseAudio not available, trying ALSA...")
            result = subprocess.run(
                ["ffmpeg", "-sources", "alsa"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            if result.returncode == 0:
                print("   Available ALSA sources:")
                print(result.stdout)
    except Exception as e:
        print(f"   ⚠ Could not list audio sources: {e}")

    # Test 3: Check camera capabilities with ffprobe
    print("\n3. Checking camera input formats (video + audio)...")
    print(f"   Running: ffmpeg -f v4l2 -list_formats all -i {camera_device}")
    try:
        result = subprocess.run(
            ["ffmpeg", "-f", "v4l2", "-list_formats", "all", "-i", camera_device],
            check=False,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        # FFmpeg writes format info to stderr
        output = result.stderr
        print(output)

        # Check if audio mentioned
        if "audio" in output.lower():
            print("   ✓ Audio capabilities detected!")
        else:
            print("   ℹ No audio mentioned in camera capabilities")

    except Exception as e:
        print(f"   ⚠ Could not query camera: {e}")

    # Test 4: Try to detect audio input with ffprobe
    print("\n4. Attempting to probe audio from camera...")
    print(f"   Running: ffprobe -show_streams {camera_device}")
    try:
        result = subprocess.run(
            ["ffprobe", "-show_streams", camera_device],
            check=False,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        output = result.stderr + result.stdout

        if "codec_type=audio" in output:
            print("   ✓ Audio stream detected in camera!")
            print("\n   Relevant audio info:")
            for line in output.split("\n"):
                if any(
                    keyword in line.lower()
                    for keyword in ["audio", "codec_type", "sample_rate", "channels"]
                ):
                    print(f"   {line}")
        else:
            print("   ℹ No audio stream detected")

    except Exception as e:
        print(f"   ⚠ Could not probe camera: {e}")

    # Test 5: Check for USB audio devices
    print("\n5. Checking for USB audio devices...")
    print("   Running: arecord -l")
    try:
        result = subprocess.run(
            ["arecord", "-l"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
        if result.returncode == 0 and result.stdout.strip():
            print("   Available audio capture devices:")
            print(result.stdout)

            # Check if USB camera appears
            if "usb" in result.stdout.lower() or "webcam" in result.stdout.lower():
                print(
                    "\n   ✓ USB audio device found - your camera likely has a microphone!",
                )
                print(
                    "   Note the 'card' and 'device' numbers above (e.g., card 1: USB PnP)",
                )
        else:
            print("   No audio capture devices found")

    except FileNotFoundError:
        print(
            "   ℹ 'arecord' not found (install alsa-utils: sudo apt-get install alsa-utils)",
        )
    except Exception as e:
        print(f"   ⚠ Could not list audio devices: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("\nSUMMARY:")
    print("--------")
    print("\nIf you see audio devices listed above, your camera likely supports audio.")
    print("\nTo enable audio in your recordings:")
    print("1. Note the audio device (e.g., 'hw:1,0' from arecord output)")
    print("2. Edit recording/constants.py and set CAPTURE_AUDIO = True")
    print("3. Update get_ffmpeg_command() to include audio input options")
    print("\nIf NO audio devices appear, your camera doesn't have a microphone.")
    print("You would need to:")
    print("  - Use a USB microphone")
    print("  - Use the Raspberry Pi's built-in audio input (if available)")
    print("  - Use a different camera with a built-in mic")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    check_camera_audio_support()
