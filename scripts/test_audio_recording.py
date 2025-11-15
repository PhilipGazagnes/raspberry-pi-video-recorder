#!/usr/bin/env python3
"""
Test audio recording functionality.

This script tests if the updated FFmpeg command can capture both
video and audio from the camera.

Usage:
    python scripts/test_audio_recording.py

This will:
1. Create a 10-second test recording with audio
2. Check if the video file has both video and audio streams
3. Display audio stream information
"""

import subprocess
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from recording.constants import get_ffmpeg_command


def test_audio_recording() -> None:
    """Test recording with audio enabled."""
    print("=" * 60)
    print("Audio Recording Test")
    print("=" * 60)

    # Create test output file
    output_file = Path("/tmp/test_audio_recording.mp4")
    camera_device = "/dev/video0"
    duration = 10  # 10 seconds

    print(f"\nTest parameters:")
    print(f"  Camera: {camera_device}")
    print(f"  Output: {output_file}")
    print(f"  Duration: {duration} seconds")
    print()

    # Get FFmpeg command
    command = get_ffmpeg_command(
        input_device=camera_device,
        output_file=str(output_file),
    )

    # Add duration limit
    command.insert(-1, "-t")
    command.insert(-1, str(duration))

    print("Generated FFmpeg command:")
    print("  " + " ".join(command))
    print()

    # Check if audio input is included
    if "-f" in command and "alsa" in command:
        print("✓ Audio input detected in command")
    else:
        print("✗ WARNING: No audio input in command!")
        print("  Make sure CAPTURE_AUDIO = True in recording/constants.py")
        return

    # Start recording
    print(f"\nStarting {duration}-second test recording...")
    print("(Make some noise so we can verify audio is captured!)")
    print()

    try:
        # Run FFmpeg
        start_time = time.time()
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=duration + 10,  # Add buffer for startup/shutdown
            check=False,
        )

        elapsed = time.time() - start_time

        print(f"Recording completed in {elapsed:.1f} seconds")
        print()

        # Check if file was created
        if not output_file.exists():
            print("✗ ERROR: Output file was not created!")
            print("\nFFmpeg stderr:")
            print(process.stderr)
            return

        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"✓ Output file created: {output_file}")
        print(f"  File size: {file_size_mb:.2f} MB")
        print()

        # Analyze the file with ffprobe
        print("Analyzing recorded file...")
        probe_result = subprocess.run(
            ["ffprobe", "-show_streams", "-of", "json", str(output_file)],
            capture_output=True,
            text=True,
            timeout=5.0,
            check=False,
        )

        if probe_result.returncode != 0:
            print("✗ ERROR: Could not analyze file with ffprobe")
            print(probe_result.stderr)
            return

        # Check for video and audio streams
        output = probe_result.stdout

        has_video = '"codec_type": "video"' in output
        has_audio = '"codec_type": "audio"' in output

        print("\nStream analysis:")
        print(f"  Video stream: {'✓ Present' if has_video else '✗ Missing'}")
        print(f"  Audio stream: {'✓ Present' if has_audio else '✗ Missing'}")
        print()

        if has_video and has_audio:
            print("🎉 SUCCESS! Recording has both video and audio!")
            print()
            print("Detailed audio stream info:")
            # Get detailed audio info
            audio_probe = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-select_streams",
                    "a:0",
                    "-show_entries",
                    "stream=codec_name,sample_rate,channels,bit_rate",
                    "-of",
                    "default=noprint_wrappers=1",
                    str(output_file),
                ],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
            print(audio_probe.stdout)
            print(
                f"\nYou can play the test video to verify audio: "
                f"ffplay {output_file}",
            )
        elif has_video and not has_audio:
            print("⚠ WARNING: Video recorded but NO AUDIO stream!")
            print()
            print("Possible issues:")
            print("  1. Audio device not accessible (permission issue?)")
            print("  2. Wrong audio device configured")
            print("  3. FFmpeg audio codec not available")
            print()
            print("FFmpeg stderr:")
            print(process.stderr)
        else:
            print("✗ ERROR: Recording failed!")
            print()
            print("FFmpeg stderr:")
            print(process.stderr)

    except subprocess.TimeoutExpired:
        print("✗ ERROR: Recording timed out!")
    except Exception as e:
        print(f"✗ ERROR: {e}")

    print()
    print("=" * 60)


if __name__ == "__main__":
    test_audio_recording()
