# Upload Module - Setup Guide

Complete guide for setting up YouTube video uploads for the Boxing Club Recording System.

## Overview

The upload module provides:
- ✅ Automated YouTube uploads with OAuth 2.0
- ✅ Resumable uploads (handles network interruptions)
- ✅ Automatic playlist management
- ✅ Clean, simple API for main service
- ✅ Comprehensive error handling
- ✅ No manual intervention after initial setup

## Prerequisites

1. **Google Cloud Project** (you already have this)
2. **YouTube channel** to upload to
3. **Python 3.8+**
4. **Network access** to YouTube API

---

## Setup Steps

### Step 1: Install Dependencies

```bash
pip install -r requirements_upload.txt
```

This installs:
- `google-auth` - OAuth authentication
- `google-auth-oauthlib` - OAuth flow
- `google-api-python-client` - YouTube API
- `python-dotenv` - Environment variables

### Step 2: Google Cloud Console Setup

#### 2.1 Enable YouTube Data API v3

1. Go to: https://console.cloud.google.com/apis/library
2. Select your project
3. Search: "YouTube Data API v3"
4. Click **Enable**

#### 2.2 Configure OAuth Consent Screen

1. Go to: https://console.cloud.google.com/apis/credentials/consent
2. Choose **External** (if personal account) or **Internal** (if workspace)
3. Fill in required fields:
   - App name: "Boxing Club Recorder"
   - User support email: Your email
   - Developer contact: Your email
4. **Scopes**: Add:
   - `https://www.googleapis.com/auth/youtube.upload`
   - `https://www.googleapis.com/auth/youtube`
5. **Test users**: Add your Google account email
6. Save and continue

#### 2.3 Create OAuth Credentials

1. Go to: https://console.cloud.google.com/apis/credentials
2. Click **Create Credentials** > **OAuth client ID**
3. Application type: **Desktop app**
4. Name: "Boxing Club Recorder"
5. Click **Create**
6. **Download JSON** → save as `credentials/client_secret.json`

⚠️ **Keep this file secret!** It contains your OAuth credentials.

### Step 3: Create YouTube Playlist

1. Go to YouTube Studio: https://studio.youtube.com
2. Left menu: **Playlists** > **New Playlist**
3. Name: "Boxing Club Sessions"
4. Visibility: **Unlisted**
5. After creation, click on playlist
6. Copy **Playlist ID** from URL: `?list=PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Step 4: Configure Environment

#### 4.1 Create credentials directory

```bash
mkdir -p credentials
```

#### 4.2 Copy environment template

```bash
cp .env.example .env
```

#### 4.3 Edit .env file

```bash
# YouTube OAuth credentials
YOUTUBE_CLIENT_SECRET_PATH=credentials/client_secret.json
YOUTUBE_TOKEN_PATH=credentials/token.json

# Your playlist ID (from Step 3)
YOUTUBE_PLAYLIST_ID=PLxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 5: Initial Authentication

**Run this ONCE** to authenticate:

```bash
python setup_youtube_auth.py
```

This will:
1. Open your browser
2. Ask you to log in to Google
3. Request permissions for YouTube access
4. Generate `credentials/token.json`

✅ After this, uploads are **fully automated** - no more browser logins!

**Token refresh**: The token automatically refreshes and never expires (unless you revoke it).

---

## Usage

### Basic Upload

```python
from upload import UploadController

# Initialize controller (reads from .env)
controller = UploadController()

# Upload video
result = controller.upload_video(
    video_path="/recordings/2025-10-12_18-30-45.mp4",
    timestamp="2025-10-12 18:30:45"
)

if result.success:
    print(f"✅ Uploaded! Video ID: {result.video_id}")
    print(f"Duration: {result.upload_duration:.1f}s")
    print(f"Size: {result.file_size / (1024 * 1024):.1f} MB")
else:
    print(f"❌ Upload failed: {result.error_message}")
    print(f"Status: {result.status.value}")
```

### Test Connection

```python
# Check if ready to upload
if controller.is_ready():
    print("✅ Ready to upload")
else:
    print("❌ Not ready - check authentication")

# Test YouTube API connection
if controller.test_connection():
    print("✅ YouTube connection OK")
else:
    print("❌ Cannot connect to YouTube")
```

### Main Service Integration

```python
from upload import UploadController, UploadStatus

class MainService:
    def __init__(self):
        self.uploader = UploadController()

    def handle_recording_complete(self, video_path, timestamp):
        """Called when recording finishes"""

        # Upload video
        result = self.uploader.upload_video(video_path, timestamp)

        if result.success:
            # Update storage with video ID
            self.storage.mark_uploaded(video_path, result.video_id)

            # Optional: Delete local file
            # os.remove(video_path)

            # Log success
            self.logger.info(
                f"Upload complete: {result.video_id} "
                f"({result.upload_duration:.1f}s)"
            )
        else:
            # Handle failure
            if result.status == UploadStatus.NETWORK_ERROR:
                # Queue for retry
                self.upload_queue.add(video_path, timestamp)
            elif result.status == UploadStatus.AUTH_ERROR:
                # Critical - alert admin
                self.alert_admin("YouTube auth failed!")
            else:
                # Log error
                self.logger.error(f"Upload failed: {result.error_message}")
```

---

## File Structure

```
project/
├── .env                          # Your configuration
├── setup_youtube_auth.py         # One-time auth script
├── credentials/
│   ├── client_secret.json       # From Google Cloud (SECRET!)
│   └── token.json               # Generated by setup (SECRET!)
└── upload/
    ├── __init__.py
    ├── constants.py              # Configuration constants
    ├── factory.py               # Dependency injection
    ├── auth/
    │   ├── __init__.py
    │   └── oauth_manager.py     # OAuth handling
    ├── interfaces/
    │   ├── __init__.py
    │   └── uploader_interface.py # Abstract contract
    ├── implementations/
    │   ├── __init__.py
    │   ├── youtube_uploader.py   # Real YouTube API
    │   └── mock_uploader.py      # Testing mock
    └── controllers/
        ├── __init__.py
        └── upload_controller.py  # High-level API
```

---

## Troubleshooting

### "client_secret.json not found"

**Fix**: Download OAuth credentials from Google Cloud Console and save to correct path.

### "token.json not found"

**Fix**: Run `python setup_youtube_auth.py` to authenticate.

### "Credentials invalid and cannot be refreshed"

**Fix**:
1. Delete `credentials/token.json`
2. Run `python setup_youtube_auth.py` again

### "Upload failed: 403 Forbidden"

**Possible causes**:
- OAuth consent screen not configured
- Scopes not granted during authentication
- YouTube Data API not enabled

**Fix**:
1. Check API is enabled in Google Cloud Console
2. Re-run authentication with correct scopes

### "Upload timeout"

**Possible causes**:
- Large file + slow network
- Network interruption

**Fix**:
- Check UPLOAD_TIMEOUT in constants.py (default: 600s)
- Verify network stability
- Check file size isn't excessive

### "Quota exceeded"

YouTube has upload quotas:
- Default: 10,000 units/day
- 1 upload ≈ 1,600 units
- ~6 videos/day by default

**Fix**:
- Request quota increase in Google Cloud Console
- Or reduce uploads per day

---

## Security Notes

### Files to Keep Secret

⚠️ **NEVER commit these to Git**:
- `credentials/client_secret.json`
- `credentials/token.json`
- `.env`

Add to `.gitignore`:
```
.env
credentials/
```

### Token Security

- `token.json` grants full YouTube access
- Store securely on Raspberry Pi
- Use file permissions: `chmod 600 credentials/token.json`
- Revoke via Google Account settings if compromised

---

## Testing

### Test with Mock Uploader

```python
from upload import UploadController
from upload.implementations.mock_uploader import MockUploader

# Create mock for testing
mock = MockUploader(simulate_timing=False)
controller = UploadController(uploader=mock)

# Upload (instant, no YouTube API)
result = controller.upload_video(
    video_path="/path/to/test.mp4",
    timestamp="2025-10-12 18:30:45"
)

# Check mock history
print(mock.get_upload_history())
```

---

## API Reference

### UploadController

Main interface for uploads.

**Methods**:
- `upload_video(video_path, timestamp, playlist_id=None)` - Upload video
- `test_connection()` - Test YouTube API
- `is_ready()` - Check if authenticated
- `get_status()` - Get controller status
- `set_default_playlist(playlist_id)` - Change default playlist

### UploadResult

Upload operation result.

**Attributes**:
- `success: bool` - Upload succeeded
- `video_id: str | None` - YouTube video ID
- `status: UploadStatus` - Status code
- `error_message: str | None` - Error description
- `upload_duration: float` - Upload time (seconds)
- `file_size: int` - File size (bytes)

### UploadStatus

Status codes for uploads.

**Values**:
- `SUCCESS` - Upload completed
- `FAILED` - Generic failure
- `TIMEOUT` - Upload timed out
- `AUTH_ERROR` - Authentication failed
- `NETWORK_ERROR` - Network issue
- `INVALID_FILE` - Invalid video file
- `QUOTA_EXCEEDED` - API quota exceeded

---

## Performance

### Upload Speed

Typical estimates (1080p H.264, ~750 MB file):
- Good connection (10 Mbps up): ~10 minutes
- Moderate connection (5 Mbps up): ~20 minutes
- Slow connection (2 Mbps up): ~50 minutes

### Memory Usage

- Chunk-based upload: Uses ~10 MB RAM
- No need to load entire file in memory

### CPU Usage

- Minimal during upload (network-bound)
- No transcoding (uploads original file)

---

## Next Steps

1. ✅ Complete Google Cloud setup
2. ✅ Run authentication script
3. ✅ Test with sample video
4. ✅ Integrate with main service
5. ✅ Monitor initial uploads
6. ✅ Set up error alerting

---

## Support

For issues:
1. Check this README
2. Review logs for error details
3. Verify Google Cloud configuration
4. Test with mock uploader first
