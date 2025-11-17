#!/usr/bin/env python3
"""
Remote Control Script

Send commands to the recorder service remotely (via SSH or locally).

Usage:
    python scripts/remote_control.py start      # Start recording
    python scripts/remote_control.py stop       # Stop recording
    python scripts/remote_control.py extend     # Extend recording by 5 min
    python scripts/remote_control.py status     # Show status

Or directly from SSH:
    ssh pi@raspberrypi "python /opt/raspberry-pi-video-recorder/scripts/remote_control.py start"

Or even simpler:
    ssh pi@raspberrypi "echo START > /tmp/recorder_control.cmd"

How it works:
- Writes command to control file (/tmp/recorder_control.cmd)
- Service checks this file every loop iteration (~100ms)
- File is deleted after processing
- Response time: typically <1 second
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import CONTROL_FILE


def send_command(command: str) -> bool:
    """
    Send a command to the recorder service.

    Args:
        command: Command to send (START, STOP, EXTEND, STATUS)

    Returns:
        True if command was sent successfully, False otherwise
    """
    command = command.upper()
    valid_commands = ["START", "STOP", "EXTEND", "STATUS"]

    if command not in valid_commands:
        print(f"❌ Invalid command: {command}")
        print(f"Valid commands: {', '.join(valid_commands)}")
        return False

    try:
        # Write command to control file
        control_file = Path(CONTROL_FILE)
        control_file.write_text(command)
        print(f"✅ Command sent: {command}")
        print(f"Service will process it within ~1 second")
        return True

    except Exception as e:
        print(f"❌ Failed to send command: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Send commands to the recorder service remotely",
        epilog="""
Examples:
  %(prog)s start      # Start recording
  %(prog)s stop       # Stop recording
  %(prog)s extend     # Extend recording by 5 minutes
  %(prog)s status     # Show current status in service logs
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "command",
        choices=["start", "stop", "extend", "status"],
        help="Command to send to recorder service",
    )

    args = parser.parse_args()

    success = send_command(args.command)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
