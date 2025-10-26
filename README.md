# Raspberry Pi Video Recorder

A generic, production-ready video recording system for Raspberry Pi. Domain-agnostic and reusable - easily customizable for any use case (sports training, security, events, etc.).

## Project Overview

Single-camera video recording system with hardware button control. Users press a button to start/stop recording, videos auto-upload to YouTube in the background with LED status feedback and silent operation.

**System Design Philosophy:**
- **Recording is Priority #1**: Users can record unlimited videos back-to-back
- **Uploads are Invisible**: Background upload queue processes videos when possible
- **No Waiting**: System returns to READY immediately after saving recording
- **Network Resilience**: Failed uploads auto-retry with configurable delays
- **Simple Operation**: One button, three LEDs, zero user intervention needed

**Key Features:**
- 🎥 One-button video recording (start/stop/extend)
- 📤 Silent background upload queue to YouTube
- 💡 LED status indicators (Green=Ready, Orange=Busy, Red=Error)
- 🔇 Silent operation (no audio feedback during normal operation)
- 📦 Modular SOLID architecture
- 🧪 Fully testable without hardware
- ⚙️ Centralized configuration
- 🔄 Automatic retry on upload failures
- 🧹 Automatic cleanup of old uploaded videos

---

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Raspberry Pi (tested on Pi 5)
- USB webcam (1080p recommended)
- Optional: GPIO hardware (button, LEDs, speaker)

### Installation

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd raspberry-pi-video-recorder
   ```

2. **Configure the system:**

   a. Copy and edit the main configuration file:
   ```bash
   cp config/settings.py config/settings.py.local  # Optional: keep custom config separate
   ```

   b. Edit `config/settings.py` to customize:
   - GPIO pin assignments
   - Recording duration and video quality
   - Storage paths and retention policies
   - Video title prefix (change from generic "Video Session" to your domain)

   c. Setup YouTube authentication:
   ```bash
   # Copy the .env template
   cp .env.example .env

   # Edit .env and set the paths (defaults should work):
   YOUTUBE_CLIENT_SECRET_PATH=credentials/client_secret.json
   YOUTUBE_TOKEN_PATH=credentials/token.json
   YOUTUBE_PLAYLIST_ID=your_playlist_id_here  # Optional
   ```

   d. Authenticate with YouTube (one-time setup):
   ```bash
   # Download client_secret.json from Google Cloud Console
   # Place it in credentials/client_secret.json

   # Run authentication setup (opens browser)
   python setup_youtube_auth.py

   # This creates credentials/token.json for automatic uploads
   ```

3. **Install dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Virtual environment** will be automatically configured if using VS Code

---

## Configuration Guide

### 📋 Centralized Configuration

**ALL configuration lives in `config/settings.py`** - this is your single source of truth.

#### What You Can Configure:

**Hardware:**
- GPIO pin assignments (button, LEDs)
- Audio/TTS settings (rate, volume, speaker device)

**Recording:**
- Video resolution, FPS, codec settings
- Recording durations (default, extension, maximum)
- Camera device path

**Storage:**
- Storage base path and directory structure
- Space thresholds and retention policies
- Upload retry configuration
- Auto-cleanup settings

**Upload:**
- Video title prefix (customize for your domain!)
- Default tags and privacy settings
- YouTube category
- Upload timeout and chunk size

#### Example Customization:

```python
# config/settings.py

# Change this to match your use case
SESSION_TITLE_PREFIX = "Training Session"  # "Security Footage", "Event Recording", etc.
DEFAULT_VIDEO_TAGS = ["training", "gym", "workout"]  # Customize for your domain

# Adjust recording quality
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 30

# Storage retention
UPLOADED_RETENTION_DAYS = 14  # Keep videos for 2 weeks
MAX_UPLOADED_VIDEOS = 50
```

### 🔐 Secrets Management

**NEVER commit credentials to version control!**

This project uses **file-based OAuth** for YouTube uploads:

1. **Download credentials from Google Cloud Console**:
   - Create a project and enable YouTube Data API v3
   - Create OAuth 2.0 credentials (Desktop app type)
   - Download `client_secret.json`
   - Place in `credentials/client_secret.json`

2. **Authenticate once** (creates token.json):
   ```bash
   python setup_youtube_auth.py
   ```
   This opens a browser for you to grant permissions. The token is saved and refreshed automatically.

3. **Configure .env** (paths to credential files):
   ```bash
   # .env (NEVER commit this file!)
   YOUTUBE_CLIENT_SECRET_PATH=credentials/client_secret.json
   YOUTUBE_TOKEN_PATH=credentials/token.json
   YOUTUBE_PLAYLIST_ID=your_playlist_id  # Optional
   ```

The `credentials/` directory is already in `.gitignore` - your secrets are safe!

---

## Domain-Agnostic Design

This system is intentionally **generic** - no hardcoded business logic. To adapt it for your use case:

1. **Change video titles**: Edit `SESSION_TITLE_PREFIX` in `config/settings.py`
2. **Customize tags**: Modify `DEFAULT_VIDEO_TAGS` for your domain
3. **Adjust voice prompts**: Edit `AUDIO_MESSAGE_TEXTS` in `hardware/constants.py`
4. **Configure retention**: Set `UPLOADED_RETENTION_DAYS` based on your needs

### Example Use Cases:
- **Sports Training**: "Training Session 2025-01-15 14:30"
- **Security Camera**: "Security Recording 2025-01-15 14:30"
- **Dance Studio**: "Class Recording 2025-01-15 14:30"
- **Lecture Recording**: "Lecture 2025-01-15 14:30"

Simply change one config value and the entire system adapts!

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


## Hardware Configuration
- **Controller**: Raspberry Pi 5 (8GB)
- **Camera**: USB webcam (1080p)
- **Interface**: Push button + 3-LED dashboard (Green/Orange/Red)
- **Audio**: USB mini speaker for voice prompts
- **Connectivity**: Ethernet primary, WiFi backup

## GPIO Pin Configuration

Configure these in `config/settings.py`:
```python
GPIO_BUTTON_PIN = 18    # Button input pin
GPIO_LED_GREEN = 12     # Green LED (ready/recording)
GPIO_LED_ORANGE = 16    # Orange LED (processing)
GPIO_LED_RED = 20       # Red LED (error)
```

## System Behavior

### Recording Workflow (Typical Day)

**Morning - System Startup:**
1. Pi boots, service starts automatically
2. Green LED turns solid → System READY
3. Silent (no audio feedback)

**During Day - Continuous Recording:**
1. **Start Recording**: Single button press
   - Green LED starts blinking
   - Recording begins (10 minutes default)
   - Silent operation

2. **Extend Recording** (optional): Double button press during recording
   - Adds 5 minutes (max 25 minutes total)
   - Silent operation

3. **Stop Recording**: Single button press (or auto-stop at duration limit)
   - Green LED stops blinking
   - Orange LED turns on briefly (2-3 seconds while saving to storage)
   - Video saved to storage database
   - **Green LED returns immediately** → System READY for next recording
   - Upload queued in background (invisible to user)

4. **Back-to-back recordings**: Repeat step 1 immediately
   - No waiting for uploads to complete
   - Record as many videos as needed
   - Uploads process in background queue (oldest first, one at a time)

**Background Operations (Invisible to User):**

- **Upload Queue**:
  - Processes videos in order (oldest first)
  - One upload at a time
  - Can run during new recordings
  - Silent on success
  - Auto-retries on failure (wait 5 minutes, retry when idle)
  - Max 2 retry attempts per video

- **Automatic Cleanup**:
  - Runs every hour
  - Deletes uploaded videos after 7 days OR when 30 videos reached
  - Keeps disk space available

### LED Status Guide

- **Green Solid**: System ready for recording
- **Green Blinking**: Recording in progress
- **Orange Solid**: System busy (saving/processing) - brief (2-3 seconds)
- **Red Solid**: Error state (disk full, camera error, etc.)

### Error Handling

**Disk Full:**
- Red LED solid
- Cannot record new videos
- Recovery: Single button press (checks if cleanup freed space)

**Camera Error:**
- Red LED solid
- Cannot start recording
- Recovery: Single button press (re-checks camera availability)

**Upload Failure:**
- Silent (no LED change)
- Logged to `/var/log/recorder-service.log`
- Auto-retry after 5 minutes when system idle
- Check logs via SSH: `tail -f /var/log/recorder-service.log`

**Network Issues:**
- Uploads fail with network error logged
- System continues recording normally
- Uploads retry automatically when network restored
- No user intervention needed

### Monitoring & Logs

**Check system status:**
```bash
# SSH into Raspberry Pi
ssh pi@<raspberry-pi-ip>

# View live logs
tail -f /var/log/recorder-service.log

# View recent errors
grep ERROR /var/log/recorder-service.log | tail -20

# View upload status
grep -i upload /var/log/recorder-service.log | tail -20

# Check disk space
df -h /home/pi/videos
```

**Log files:**
- Location: `/var/log/recorder-service.log`
- Automatic rotation: Daily, keeps 7 days
- Max size per file: 10MB
- What's logged:
  - Recording start/stop with timestamps
  - Upload successes/failures with error details
  - Network errors with diagnostic info
  - Cleanup operations
  - Error recovery attempts

## Key Design Principles

- State-Driven: All behavior controlled by central state machine
- Non-Blocking: Background operations don't interfere with recording
- Fault-Tolerant: Comprehensive error handling with recovery
- Modular: Each component independently testable
- Extensible: Easy to add features (multiple cameras, etc.)
