# Hardware Configuration
GPIO_BUTTON_PIN = 18
GPIO_LED_GREEN = 12
GPIO_LED_ORANGE = 16
GPIO_LED_RED = 20

# Recording Configuration
DEFAULT_RECORDING_DURATION = 600  # 10 minutes
EXTENSION_DURATION = 300  # 5 minutes
MAX_RECORDING_DURATION = 1500  # 25 minutes
WARNING_TIME = 60  # 1 minute before end

# Storage Configuration
VIDEO_STORAGE_PATH = "/home/pi/recordings"
MAX_STORAGE_GB = 50
CLEANUP_THRESHOLD = 80  # Percent full before cleanup

# YouTube Configuration
YOUTUBE_CLIENT_ID = "your_client_id"
YOUTUBE_CLIENT_SECRET = "your_client_secret"
UPLOAD_QUEUE_SIZE = 10

# Audio Configuration
TTS_RATE = 150
TTS_VOLUME = 0.8
SPEAKER_DEVICE = "hw:1,0"  # USB speaker
