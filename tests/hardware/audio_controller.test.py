print("Starting audio test...")

from hardware.audio_controller import AudioController
import time

audio = AudioController()

# Test basic functionality - all messages are automatically queued
print("Playing message 1...")
audio.play_text("C'est la fête de la musique")

print("Playing message 2...")
audio.play_text("On boit du champagne")

print("Playing message 3...")
audio.play_text("Au revoir")

# Wait for all messages to complete
while audio.is_playing():
    print(f"Still playing... Queue size: {audio.get_queue_size()}")
    time.sleep(1)

print("Test complete")
