# Raspberry Pi Video Recorder

A Python service for recording videos on Raspberry Pi with hardware button control.

## Project Overview

Multi-camera video recording system for practice analysis. Users hit a button to start/stop recording, videos auto-upload to YouTube with LED status feedback and voice prompts.

### Prerequisites

- Python 3.8 or higher
- Virtual environment (automatically created)

### Installation

1. Clone the repository and navigate to the project directory
2. The Python virtual environment will be automatically configured when you open the project in VS Code

### Development Tools

This project uses the following tools for code quality:

- **Ruff**: Modern, fast Python linter and formatter
- **Black**: Code formatter for consistent style
- **isort**: Import statement organizer
- **mypy**: Static type checker

#### Manual Linting and Formatting

Run all linting and formatting tools:
```bash
./lint.sh
```

Or run individual tools:
```bash
# Linting with Ruff
.venv/bin/ruff check . --fix

# Format imports
.venv/bin/isort .

# Format code with Black
.venv/bin/black .

# Type checking
.venv/bin/mypy . --ignore-missing-imports
```

### VS Code Configuration

The project includes VS Code settings that will:
- Automatically format Python files on save
- Use the correct Python interpreter from the virtual environment
- Show linting errors inline
- Organize imports automatically

## System Architecture

### Core Components

#### Main Service Controller (`recorder_service.py`)
**Role**: Central coordinator and state manager
- Manages the main state machine (READY → RECORDING → PROCESSING → READY)
- Coordinates all other components
- Handles systemd service lifecycle
- Implements graceful shutdown

#### State Machine (`core/state_machine.py`)
**Role**: System state management and coordination
- **States**: BOOTING, READY, RECORDING, PROCESSING, ERROR
- **Button Logic**:
  - READY: Single press = start recording
  - RECORDING: Single press = stop, Double press = extend (+5min)
  - ERROR: Single press = attempt recovery
- **Callbacks**: Notifies other components of state changes

#### Hardware Controllers

**LED Controller (`hardware/led_controller.py`)**
- **OFF**: All LEDs off (system booting)
- **READY**: Green solid (ready to record)
- **RECORDING**: Green blinking (recording in progress)
- **PROCESSING**: Orange solid (uploading/processing)
- **ERROR**: Red solid (error state)

**Button Controller (`hardware/button_controller.py`)**
- GPIO input with debouncing (50ms)
- Single vs double-tap detection (500ms window)
- Interrupt-based, non-blocking operation
- Simulation mode for development without GPIO

**Audio Controller (`hardware/audio_controller.py`)**
- Text-to-Speech (TTS) voice prompts
- Non-blocking audio playbook
- Predefined message library
- USB speaker support

#### Recording System

**Camera Manager (`recording/camera_manager.py`)**
- FFmpeg integration for video capture
- 1080p recording capability
- Process management for recording sessions
- Camera health monitoring

**Recording Session (`recording/recording_session.py`)**
- Session lifecycle management
- Duration tracking (10min default)
- Extension capability (+5min, max 25min total)
- Time-based warnings (1-minute remaining)

#### Background Processing

**Upload Manager (`upload/upload_manager.py`)**
- Background YouTube upload queue
- Concurrent recording + uploading
- Retry logic for failed uploads
- Thread pool for multiple uploads

**Storage Manager (`storage/storage_manager.py`)**
- Disk space monitoring
- Automated file cleanup
- Timestamped filename generation
- Storage threshold warnings

## File Structure

```
video-recorder/
├── recorder_service.py              # Main service coordinator
├── config/
│   ├── __init__.py
│   └── settings.py                  # All configuration parameters
├── core/
│   ├── __init__.py
│   ├── state_machine.py            # State management and transitions
│   ├── error_handler.py            # Error recovery logic
│   └── event_bus.py                # Inter-component communication
├── hardware/
│   ├── __init__.py
│   ├── led_controller.py           # 3-LED status dashboard
│   ├── button_controller.py        # Button input with debouncing
│   └── audio_controller.py         # TTS voice feedback
├── recording/
│   ├── __init__.py
│   ├── camera_manager.py           # FFmpeg video capture
│   └── recording_session.py        # Session management
├── upload/
│   ├── __init__.py
│   └── upload_manager.py           # YouTube API integration
└── storage/
    ├── __init__.py
    └── storage_manager.py          # File and space management
```

## Hardware Configuration
- **Controller**: Raspberry Pi 5 (8GB)
- **Camera**: USB webcam (1080p)
- **Interface**: Push button + 3-LED dashboard (Green/Orange/Red)
- **Audio**: USB mini speaker for voice prompts
- **Connectivity**: Ethernet primary, WiFi backup

## GPIO Pin Configuration

(from config/settings.py)
- GPIO_BUTTON_PIN = 18
- GPIO_LED_GREEN = 12
- GPIO_LED_ORANGE = 16
- GPIO_LED_RED = 20

## System Behavior

### Recording Workflow

- System Ready: Green LED solid, "System ready" voice prompt
- Start Recording: Single button press → Green LED blinking, "Recording started"
- Extension: Double button press during recording → "5 minutes added"
- Warning: At 9 minutes → "One minute remaining, press button twice to extend"
- Stop Recording: Single button press → Orange LED, "Recording complete, uploading"
- Ready: Background upload complete → Green LED, "Ready for next recording"

### Error Handling

- Storage Full: Red LED, "Memory full" voice prompt
- Camera Error: Red LED, "Camera error" voice prompt
- Network Down: Red LED, "Network disconnected" voice prompt
- Recovery: Single button press in error state attempts recovery

### Audio Feedback Messages

- System startup: "System ready"
- Recording start: "Recording started"
- 9-minute warning: "One minute remaining, press button twice to extend"
- Extension confirmed: "5 minutes added, recording continues"
- Recording stop: "Recording complete, uploading"
- Ready state: "Ready for next recording"
- Upload complete: "Upload successful"
- Error states: "Memory full" / "Network disconnected" / "Camera error"

## Development Status

- ✅ State Machine: Complete with full state management
- ✅ LED Controller: Complete with all status patterns
- ✅ Button Controller: Complete with debouncing and double-tap
- ✅ Audio Controller: Complete with full TTS voice feedback
- 📝 Camera Manager: Not started
- 📝 Recording Session: Not started
- 📝 Upload Manager: Not started
- 📝 Storage Manager: Not started
- 📝 Main Service Integration: Waiting for all controllers

## Key Design Principles

- State-Driven: All behavior controlled by central state machine
- Non-Blocking: Background operations don't interfere with recording
- Fault-Tolerant: Comprehensive error handling with recovery
- Modular: Each component independently testable
- Extensible: Easy to add features (multiple cameras, etc.)
