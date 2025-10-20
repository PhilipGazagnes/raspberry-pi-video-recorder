# Upload Module - Quick Start Checklist

Follow these steps in order to get your upload system running.

## Pre-Setup ✓

- [ ] You have a Google Cloud Project
- [ ] You have a YouTube channel
- [ ] You have access to the Raspberry Pi (or development machine)

---

## Step 1: Create Files (5 minutes)

```bash
# Run the directory structure script
bash <directory_structure_script>

# Or manually create all files from artifacts
```

**Copy all artifacts** into their respective files:
- `upload/constants.py`
- `upload/interfaces/uploader_interface.py`
- `upload/auth/oauth_manager.py`
- `upload/implementations/youtube_uploader.py`
- `upload/implementations/mock_uploader.py`
- `upload/controllers/upload_controller.py`
- `upload/factory.py`
- All `__init__.py` files
- `setup_youtube_auth.py` (at project root)
- `.env.example`
- `requirements_upload.txt`

---

## Step 2: Install Dependencies (2 minutes)

```bash
pip install -r requirements_upload.txt
```

---

## Step 3: Google Cloud Console (10 minutes)

### Enable API
- [ ] Go to: https://console.cloud.google.com/apis/library
- [ ] Search "YouTube Data API v3"
- [ ] Click Enable

### Configure OAuth Consent Screen
- [ ] Go to: https://console.cloud.google.com/apis/credentials/consent
- [ ] Choose External/Internal
- [ ] App name: "Boxing Club Recorder"
- [ ] Add scopes:
  - `https://www.googleapis.com/auth/youtube.upload`
  - `https://www.googleapis.com/auth/youtube`
- [ ] Add test user: Your Google account email
- [ ] Save

### Create OAuth Credentials
- [ ] Go to: https://console.cloud.google.com/apis/credentials
- [ ] Create Credentials > OAuth client ID
- [ ] Type: Desktop app
- [ ] Name: "Boxing Club Recorder"
- [ ] Download JSON

---

## Step 4: Setup Credentials (3 minutes)

```bash
# Create credentials directory
mkdir credentials

# Save downloaded JSON as:
mv ~/Downloads/client_secret_*.json credentials/client_secret.json

# Copy environment template
cp .env.example .env
```

Edit `.env`:
```bash
YOUTUBE_CLIENT_SECRET_PATH=credentials/client_secret.json
YOUTUBE_TOKEN_PATH=credentials/token.json
YOUTUBE_PLAYLIST_ID=PLxxxx  # Add your playlist ID
```

---

## Step 5: Create YouTube Playlist (2 minutes)

- [ ] Go to: https://studio.youtube.com
- [ ] Left menu: Playlists > New Playlist
- [ ] Name: "Boxing Club Sessions"
- [ ] Visibility: Unlisted
- [ ] Copy playlist ID from URL: `?list=PLxxxxxxxxxx`
- [ ] Paste into `.env` file

---

## Step 6: Authenticate (5 minutes)

```bash
python setup_youtube_auth.py
```

**What happens:**
1. Browser opens automatically
2. Log in to Google (use same account as YouTube channel)
3. Grant permissions
4. `credentials/token.json` is created

✅ **After this, uploads are fully automated!**

---

## Step 7: Test Upload (2 minutes)

Create a test video or use existing file:

```python
from upload import UploadController
from datetime import datetime

controller = UploadController()

# Test connection
if controller.test_connection():
    print("✅ Connected to YouTube")
else:
    print("❌ Connection failed")
    exit(1)

# Upload test video
result = controller.upload_video(
    video_path="/path/to/test_video.mp4",
    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)

if result.success:
    print(f"✅ Test upload successful!")
    print(f"Video ID: {result.video_id}")
else:
    print(f"❌ Upload failed: {result.error_message}")
```

---

## Step 8: Integrate with Main Service (15 minutes)

Add to your main service:

```python
from upload import UploadController

class MainService:
    def __init__(self):
        self.uploader = UploadController()

    def handle_recording_complete(self, video_path, timestamp):
        result = self.uploader.upload_video(video_path, timestamp)

        if result.success:
            # Update storage
            self.storage.mark_uploaded(video_path, result.video_id)
            self.logger.info(f"Uploaded: {result.video_id}")
        else:
            # Handle failure
            self.logger.error(f"Upload failed: {result.error_message}")
            # Add retry logic
```

---

## Verification Checklist

Before going live, verify:

- [ ] Files created in correct structure
- [ ] Dependencies installed
- [ ] YouTube API enabled
- [ ] OAuth consent screen configured
- [ ] OAuth credentials downloaded
- [ ] `.env` file configured
- [ ] Playlist created and ID added to `.env`
- [ ] `setup_youtube_auth.py` completed successfully
- [ ] `credentials/token.json` exists
- [ ] Test upload successful
- [ ] Video appears in YouTube playlist
- [ ] Main service integration complete

---

## Troubleshooting

### "Module 'upload' not found"
**Fix**: Make sure you're in project root and all `__init__.py` files exist

### "YOUTUBE_CLIENT_SECRET_PATH not set"
**Fix**: Check `.env` file exists and has correct paths

### "client_secret.json not found"
**Fix**: Download OAuth credentials from Google Cloud Console

### "token.json not found"
**Fix**: Run `python setup_youtube_auth.py`

### "Upload failed: 403 Forbidden"
**Fix**: Check OAuth consent screen is configured and scopes are correct

### "Connection test failed"
**Fix**:
1. Check network connection
2. Verify YouTube API is enabled
3. Check credentials are valid

---

## Security Checklist

Before deploying:

- [ ] Add to `.gitignore`:
  ```
  .env
  credentials/
  *.json
  ```
- [ ] Set file permissions:
  ```bash
  chmod 600 credentials/client_secret.json
  chmod 600 credentials/token.json
  chmod 600 .env
  ```
- [ ] Never commit credentials to Git
- [ ] Keep credentials directory on Pi only

---

## Success! 🎉

If all steps pass, your upload system is ready!

**Next steps:**
1. Monitor first few uploads
2. Set up error alerting
3. Configure automatic retries in main service
4. Add upload analytics/logging

**Your uploads will now:**
- ✅ Happen automatically after recordings
- ✅ Use resumable upload (handles interruptions)
- ✅ Add to playlist automatically
- ✅ Refresh auth tokens automatically
- ✅ Never require manual login again

---

## Support

If you encounter issues:
1. Check each step in this checklist
2. Review UPLOAD_MODULE_README.md
3. Check logs for detailed error messages
4. Test with mock uploader first: `create_uploader(force_mock=True)`
