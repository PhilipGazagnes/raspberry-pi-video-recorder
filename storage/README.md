# Storage Module

Video storage management system for the boxing club recording project.

## Quick Start

```python
from storage import StorageController

# Initialize storage
storage = StorageController()

# Check space before recording
if not storage.check_space():
    print("Insufficient disk space!")
    return

# Save a recording
video = storage.save_recording("/tmp/recording.mp4", duration_seconds=600)

# Mark upload success
storage.mark_upload_success(video, "https://youtube.com/watch?v=xyz")

# Cleanup old videos
storage.cleanup_old_videos()

# Always cleanup
storage.cleanup()
```

## Features

- ✅ Automatic disk space monitoring
- ✅ SQLite metadata tracking
- ✅ Upload retry queue (2 attempts)
- ✅ Video validation with ffmpeg
- ✅ Automatic cleanup (7-day retention)
- ✅ Event-driven callbacks
- ✅ YAML configuration
- ✅ Mock implementation for testing

## Installation

```bash
# Install dependencies
pip install pyyaml

# Optional: Install ffmpeg for video validation
sudo apt-get install ffmpeg
```

## Directory Structure

```
/home/pi/videos/
├── pending/      # New recordings awaiting upload
├── uploaded/     # Successfully uploaded (kept 7 days)
├── failed/       # Failed uploads (retry queue)
└── corrupted/    # Videos that failed validation
```

## Configuration

Edit `config/storage.yaml`:

```yaml
storage_base_path: /home/pi/videos
min_free_space_bytes: 5368709120  # 5 GB
uploaded_retention_days: 7
max_uploaded_videos: 30
max_upload_retries: 2
```

## API Reference

### StorageController

Main interface for storage operations.

#### Recording Management

```python
# Save recording
video = storage.save_recording(
    video_path=Path("/tmp/recording.mp4"),
    duration_seconds=600  # optional
)

# Check space availability
can_record = storage.check_space()  # Returns bool

# Get storage statistics
stats = storage.get_stats()  # Returns StorageStats
```

#### Upload Management

```python
# Mark upload started
storage.mark_upload_started(video)

# Mark upload success
storage.mark_upload_success(video, youtube_url)

# Mark upload failed
storage.mark_upload_failed(video, error_message)

# Get pending uploads
pending = storage.get_pending_uploads()

# Get retry queue
retry_queue = storage.get_retry_queue()
```

#### Cleanup Operations

```python
# Cleanup old videos
count = storage.cleanup_old_videos()

# Preview cleanup (dry run)
count = storage.cleanup_old_videos(dry_run=True)

# Get cleanup summary
summary = storage.get_cleanup_summary()
```

### Event Callbacks

Register callbacks for important events:

```python
storage = StorageController()

# Disk full event
storage.on_disk_full = lambda: handle_disk_full()

# Low space warning
storage.on_low_space = lambda bytes: handle_low_space(bytes)

# Corruption detected
storage.on_corruption_detected = lambda filename: handle_corruption(filename)

# Cleanup complete
storage.on_cleanup_complete = lambda count: handle_cleanup(count)

# Storage error
storage.on_storage_error = lambda error: handle_error(error)
```

### VideoFile Model

```python
video.filename          # "recording_2025-10-04_143025.mp4"
video.filepath          # Path object
video.created_at        # datetime
video.duration_seconds  # int
video.file_size_bytes   # int
video.status            # UploadStatus enum
video.upload_attempts   # int
video.youtube_url       # str (after upload)

# Helper properties
video.exists           # bool
video.is_pending       # bool
video.is_completed     # bool
video.is_failed        # bool
video.can_retry        # bool
video.age_days         # float
```

### Upload Status States

```python
from storage import UploadStatus

UploadStatus.PENDING      # New, awaiting upload
UploadStatus.IN_PROGRESS  # Currently uploading
UploadStatus.COMPLETED    # Successfully uploaded
UploadStatus.FAILED       # Upload failed (retry queue)
UploadStatus.CORRUPTED    # File validation failed
```

## Testing

### Using Mock Storage

```python
from storage import create_storage, StorageController

# Create mock (no filesystem operations)
storage = create_storage(force_mock=True)
controller = StorageController(storage_impl=storage)

# All operations work in-memory
video = controller.save_recording("/fake/path.mp4")

# Mock has test helpers
storage.simulate_disk_full()
storage.add_fake_video("test.mp4", UploadStatus.PENDING)
```

### Unit Test Example

```python
def test_save_recording():
    storage = create_storage(force_mock=True)
    controller = StorageController(storage_impl=storage)

    video = controller.save_recording("/fake/video.mp4")

    assert video is not None
    assert video.status == UploadStatus.PENDING
    assert video.filename.startswith("recording_")
```

## Integration with Hardware Module

```python
from hardware import AudioController, LEDController
from hardware import AudioMessage, LEDPattern
from storage import StorageController

audio = AudioController()
led = LEDController()
storage = StorageController()

# Wire up events
storage.on_disk_full = lambda: (
    audio.play_message(AudioMessage.MEMORY_FULL),
    led.set_status(LEDPattern.ERROR)
)

storage.on_low_space = lambda bytes: (
    audio.play_text(f"Warning: {bytes/(1024**3):.1f} GB free")
)

# Now storage automatically triggers hardware feedback!
```

## Troubleshooting

### Disk Full Errors

```python
# Check current status
stats = storage.get_stats()
print(f"Free space: {stats.free_space_gb:.2f} GB")

# Force cleanup
storage.cleanup_old_videos()

# Check what would be cleaned
summary = storage.get_cleanup_summary()
print(f"Can free: {summary['total_size_gb']:.2f} GB")
```

### Failed Uploads

```python
# Get failed videos
retry_queue = storage.get_retry_queue()

for video in retry_queue:
    print(f"{video.filename}: {video.upload_attempts} attempts")
    print(f"Error: {video.upload_error}")
```

### Corrupted Videos

```python
# List corrupted videos
corrupted = storage.storage.list_videos(status=UploadStatus.CORRUPTED)

for video in corrupted:
    print(f"{video.filename}: {video.validation_error}")
```

## Architecture

```
storage/
├── interfaces/        # Abstract base classes
├── implementations/   # Real and mock storage
├── controllers/       # High-level API
├── managers/          # Specialized operations
├── models/           # Data structures
└── utils/            # Shared utilities
```

See [complete architecture documentation](docs/architecture.md) for details.

## License

Part of the boxing club recording system project.
