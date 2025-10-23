from upload import UploadController
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

controller = UploadController()

# Test connection
if controller.test_connection():
    print("✅ Connected to YouTube")
else:
    print("❌ Connection failed")
    exit(1)

# Upload test video
result = controller.upload_video(
    video_path="/Users/a1234/Documents/animation-musicale-ehpads.mp4",
    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)

if result.success:
    print(f"✅ Test upload successful!")
    print(f"Video ID: {result.video_id}")
else:
    print(f"❌ Upload failed: {result.error_message}")
