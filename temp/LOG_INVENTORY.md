# Logging Refactoring Inventory

This document catalogs all logging statements in the codebase, organized by module and purpose.
**Review this list and annotate with your desired changes.**

---

## Legend

- **Level**: DEBUG | INFO | WARNING | ERROR | CRITICAL
- **Type**: LIFECYCLE | STATE | OPERATION | ERROR | DEBUG | HEALTH | METRIC
- **Context**: What information is included

---

## 1. RECORDER SERVICE (Main Orchestrator)
**File**: `recorder_service.py`

### 1.1 Initialization & Lifecycle
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 108 | INFO | `"Initializing Recorder Service..."` | LIFECYCLE | Service startup |
| 147 | INFO | `"Initializing hardware controllers..."` | LIFECYCLE | Step 1 |
| 152 | INFO | `"Initializing recording system..."` | LIFECYCLE | Step 2 |
| 156 | INFO | `"Initializing storage and upload..."` | LIFECYCLE | Step 3 |
| 167 | INFO | `"Recorder Service initialized successfully"` | LIFECYCLE | Startup complete |
| 190 | INFO | `"Starting Recorder Service main loop..."` | LIFECYCLE | Main loop start |
| 206 | INFO | `"Keyboard interrupt received"` | LIFECYCLE | Shutdown trigger |
| 1104 | INFO | `"Shutting down Recorder Service..."` | LIFECYCLE | Shutdown start |
| 1149 | INFO | `"Recorder Service shutdown complete"` | LIFECYCLE | Shutdown complete |

### 1.2 State Transitions
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 421 | INFO | `"Transitioning to READY state"` | STATE | → READY |
| 428 | INFO | `"System READY for recording"` | STATE | READY confirmed |
| 432 | INFO | `"Transitioning to RECORDING state"` | STATE | → RECORDING |
| 451 | INFO | `"Transitioning to PROCESSING state"` | STATE | → PROCESSING |
| 465 | ERROR | `f"Transitioning to ERROR state: {error_message}"` | STATE | → ERROR |

### 1.3 Recording Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 555 | INFO | `"Starting new recording session"` | OPERATION | Recording start |
| 600 | INFO | `f"Recording started: {self.current_output_file.name}"` | OPERATION | Recording confirmed |
| 617 | INFO | `"Stopping recording session"` | OPERATION | Recording stop |
| 647 | INFO | `f"Recording saved to storage: {video.filename}"` | OPERATION | Saved successfully |
| 673 | INFO | `"Extending recording session"` | OPERATION | Extension request |
| 683 | INFO | `f"Recording extended by {time_str}"` | OPERATION | Extension success |
| 685 | INFO | `f"Recording extended by {extension_minutes} minutes"` | OPERATION | Extension fallback |
| 722 | INFO | `"Recording completed automatically (duration limit)"` | OPERATION | Auto-complete |

### 1.4 Upload Queue Worker
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 753 | INFO | `"Starting upload queue worker..."` | LIFECYCLE | Worker start |
| 768 | INFO | `f"Queueing upload for: {video.filename}"` | OPERATION | Video queued |
| 782 | INFO | `"Upload worker thread started"` | LIFECYCLE | Thread running |
| 806 | INFO | `"Upload worker thread stopped"` | LIFECYCLE | Thread stopped |
| 831 | INFO | `f"Starting upload: {video.filename}"` | OPERATION | Upload start |
| 848 | INFO | `f"✅ Upload successful: {video.filename} → {video_id}"` | OPERATION | Upload success (emoji) |
| 867 | INFO | `f"🔄 Retrying upload: {video.filename} (attempt {retry_count+1}/{MAX_UPLOAD_RETRIES})"` | OPERATION | Retry (emoji) |
| 904 | INFO | `f"Waiting {delay_seconds}s before retry..."` | OPERATION | Retry delay |
| 920 | INFO | `"Retry delay complete, system idle"` | OPERATION | Delay complete |

### 1.5 Cleanup Worker
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 928 | INFO | `"Starting cleanup worker..."` | LIFECYCLE | Worker start |
| 945 | INFO | `"Cleanup worker thread started"` | LIFECYCLE | Thread running |
| 953 | INFO | `"Running automatic cleanup..."` | OPERATION | Cleanup triggered |
| 959 | INFO | `f"🗑️ Deleted {summary['total_deleted']} old videos (freed {summary['space_freed_gb']:.2f} GB)"` | OPERATION | Cleanup result (emoji) |
| 974 | INFO | `"Cleanup worker thread stopped"` | LIFECYCLE | Thread stopped |

### 1.6 Network Monitor
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 982 | INFO | `"Starting network monitor..."` | LIFECYCLE | Monitor start |
| 999 | INFO | `"Network monitor thread started"` | LIFECYCLE | Thread running |
| 1025 | INFO | `"Network monitor thread stopped"` | LIFECYCLE | Thread stopped |

### 1.7 Button Handling
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 487 | INFO | `f"Button press: {press_type} in state {self.state.value}"` | OPERATION | Button event |

### 1.8 Remote Control
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 344 | INFO | `f"Remote command received: {command}"` | OPERATION | Remote cmd |
| 372 | INFO | `"Remote START → starting recording"` | OPERATION | Remote start |
| 382 | INFO | `"Remote STOP → stopping recording"` | OPERATION | Remote stop |
| 392 | INFO | `"Remote EXTEND → extending recording"` | OPERATION | Remote extend |
| 401 | INFO | `f"Remote STATUS → state={self.state.value}, ..."` | OPERATION | Remote status |

### 1.9 Recovery
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 1066 | INFO | `"Attempting recovery from ERROR state..."` | OPERATION | Recovery attempt |
| 1079 | INFO | `"Recovery successful!"` | OPERATION | Recovery success |

### 1.10 Errors & Warnings
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 233 | ERROR | `"Camera stopped unexpectedly!"` | ERROR | Camera failure |
| 559 | ERROR | `"Insufficient storage space!"` | ERROR | Disk full |
| 565 | ERROR | `"Camera not ready!"` | ERROR | Camera not ready |
| 590 | ERROR | `"Failed to start recording session"` | ERROR | Start failed |
| 614 | WARNING | `"No active session to stop"` | ERROR | Invalid stop |
| 654 | ERROR | `f"Failed to save recording: {e}"` | ERROR | Save error |
| 670 | WARNING | `"No active session to extend"` | ERROR | Invalid extend |
| 693 | WARNING | `"Failed to extend recording (max duration reached?)"` | ERROR | Extend failed |
| 710 | INFO | `f"Recording warning: {time_remaining} remaining"` | HEALTH | Time warning |
| 732 | ERROR | `f"Recording error: {error_message}"` | ERROR | Recording error |
| 803 | ERROR | `f"Upload worker error: {e}"` | ERROR | Worker error |
| 860 | ERROR | `f"Upload failed: {video.filename} - {error_msg}"` | ERROR | Upload failed |
| 876 | ERROR | `f"Upload failed permanently after {MAX_UPLOAD_RETRIES} attempts: {video.filename}"` | ERROR | Upload exhausted |
| 882 | ERROR | `f"Failed to process video in upload queue: {e}"` | ERROR | Queue error |
| 971 | ERROR | `f"Cleanup worker error: {e}"` | ERROR | Cleanup error |
| 1022 | ERROR | `f"Network monitor error: {e}"` | ERROR | Monitor error |
| 1033 | ERROR | `"Disk full!"` | ERROR | Disk full event |
| 1038 | WARNING | `"Low disk space warning"` | ERROR | Low space event |
| 1049 | ERROR | `f"Storage error: {error_message}"` | ERROR | Storage error |
| 1070 | ERROR | `"Recovery failed: Still no disk space"` | ERROR | Recovery failed |
| 1075 | ERROR | `"Recovery failed: Camera still not ready"` | ERROR | Recovery failed |
| 1095 | INFO | `f"Received signal {signal_name}, shutting down..."` | LIFECYCLE | Signal handler |

### 1.11 Debug Messages
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 506 | DEBUG | `f"{press.value} press in READY → start recording"` | DEBUG | Button logic |
| 528 | DEBUG | `f"{press.value} press ignored in PROCESSING state (busy)"` | DEBUG | Button ignored |
| 537 | DEBUG | `f"{press.value} press in ERROR → attempt recovery"` | DEBUG | Button recovery |
| 963 | DEBUG | `"Cleanup complete: no videos to delete"` | DEBUG | Nothing to clean |
| 1014 | DEBUG | `"Internet: available"` | DEBUG | Network status |
| 1016 | DEBUG | `"Internet: unavailable"` | DEBUG | Network status |

### 1.12 Service Metadata
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 256 | INFO | `f"Service restart #{new_count}"` | METRIC | Restart count |
| 260 | ERROR | `f"Failed to update restart counter: {e}"` | ERROR | Counter error |
| 309 | WARNING | `f"Failed to write heartbeat: {e}"` | ERROR | Heartbeat error |
| 351 | ERROR | `f"Failed to process control command: {e}"` | ERROR | Command error |
| 375 | WARNING | `"Remote START ignored - not in READY state"` | ERROR | Invalid remote |
| 385 | WARNING | `"Remote STOP ignored - not recording"` | ERROR | Invalid remote |
| 395 | WARNING | `"Remote EXTEND ignored - not recording"` | ERROR | Invalid remote |
| 408 | WARNING | `f"Unknown remote command: {command}"` | ERROR | Unknown cmd |
| 1108 | INFO | `"Stopping active recording session..."` | LIFECYCLE | Cleanup recording |
| 1115 | INFO | `f"Saving recording to storage: {output_file}"` | LIFECYCLE | Emergency save |
| 1125 | WARNING | `f"Failed to save recording: {e}"` | ERROR | Save failed |
| 1132 | INFO | `"Waiting for upload worker to stop..."` | LIFECYCLE | Worker wait |
| 1136 | INFO | `"Waiting for cleanup worker to stop..."` | LIFECYCLE | Worker wait |
| 1140 | INFO | `"Waiting for network monitor to stop..."` | LIFECYCLE | Worker wait |
| 1144 | INFO | `"Cleaning up hardware..."` | LIFECYCLE | Hardware cleanup |

---

## 2. CAMERA MANAGER (Recording Control)
**File**: `recording/controllers/camera_manager.py`

### 2.1 Initialization & Lifecycle
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 83 | INFO | `f"Camera Manager initialized (device: {camera_device}, capture available: {self.capture.is_available()})"` | LIFECYCLE | Initialization |
| 372 | INFO | `"Cleaning up Camera Manager"` | LIFECYCLE | Cleanup start |
| 381 | INFO | `"Camera Manager cleanup complete"` | LIFECYCLE | Cleanup done |

### 2.2 Recording Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 149 | INFO | `f"Recording started: {output_file.name} (duration: {duration or 'unlimited'}s)"` | OPERATION | Recording start |
| 157 | ERROR | `"Failed to start recording"` | ERROR | Start failed |
| 186 | INFO | `"Recording stopped"` | OPERATION | Recording stop |

### 2.3 Errors & Warnings
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 102 | WARNING | `"Camera not available"` | ERROR | Not available |
| 107 | WARNING | `"Already recording"` | ERROR | Already active |
| 132 | ERROR | `"Camera not ready to record"` | ERROR | Not ready |
| 161 | ERROR | `f"Camera error: {e}"` | ERROR | Capture error |
| 163 | ERROR | `f"Unexpected error starting recording: {e}"` | ERROR | Unexpected error |
| 180 | WARNING | `"Not recording, nothing to stop"` | ERROR | Not recording |
| 188 | WARNING | `"Failed to stop recording properly"` | ERROR | Stop failed |
| 196 | ERROR | `f"Error stopping recording: {e}"` | ERROR | Stop error |
| 280 | WARNING | `f"Camera health check failed (failures: {self._consecutive_health_failures}): {error_msg}"` | HEALTH | Health check |
| 285 | INFO | `"Camera health recovered"` | HEALTH | Health OK |
| 378 | ERROR | `f"Error during capture cleanup: {e}"` | ERROR | Cleanup error |
| 408 | WARNING | `"CameraManager not properly cleaned up - use 'with' statement or call cleanup() explicitly"` | ERROR | Cleanup warning |

---

## 3. RECORDING SESSION (Duration Management)
**File**: `recording/controllers/recording_session.py`

### 3.1 Initialization & Lifecycle
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 116 | INFO | `"Recording Session initialized"` | LIFECYCLE | Init |

### 3.2 Recording Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 144 | INFO | `f"Starting recording session: {output_file.name} ({format_duration(duration)})"` | OPERATION | Start |
| 179 | INFO | `"Recording session started successfully"` | OPERATION | Start success |
| 199 | INFO | `"Stopping recording session..."` | OPERATION | Stop |
| 215 | INFO | `"Recording session stopped successfully"` | OPERATION | Stop success |
| 259 | INFO | `f"Recording extended to {format_duration(new_limit)} (extension #{self._extension_count})"` | OPERATION | Extension |

### 3.3 Monitoring
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 357 | DEBUG | `"Monitoring thread started"` | DEBUG | Thread start |
| 383 | DEBUG | `"Monitor cleanup called from within monitor thread"` | DEBUG | Self-cleanup |
| 394 | WARNING | `"Monitoring thread did not stop within timeout (possible deadlock or hang)"` | ERROR | Thread hang |
| 397 | DEBUG | `"Monitoring thread stopped"` | DEBUG | Thread stop |
| 420 | INFO | `f"Warning: {format_duration(remaining)} remaining"` | HEALTH | Time warning |
| 428 | INFO | `"Duration limit reached, auto-stopping"` | OPERATION | Auto-stop |
| 457 | ERROR | `f"Camera health check failed: {health['error_message']}"` | HEALTH | Health fail |
| 460 | ERROR | `"Critical camera error, stopping"` | HEALTH | Critical error |

### 3.4 Errors
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 132 | ERROR | `f"Cannot start - session in state: {self.state.value}"` | ERROR | Wrong state |
| 139 | ERROR | `f"Invalid duration: {duration}s (must be 1-{MAX_RECORDING_DURATION})"` | ERROR | Invalid duration |
| 167 | ERROR | `"Failed to start camera recording"` | ERROR | Camera failed |
| 173 | ERROR | `f"Error starting session: {e}"` | ERROR | Start error |
| 195 | WARNING | `f"Cannot stop - not recording (state: {self.state.value})"` | ERROR | Wrong state |
| 218 | WARNING | `"Camera stop returned failure"` | ERROR | Stop failed |
| 223 | ERROR | `f"Error stopping session: {e}"` | ERROR | Stop error |
| 241 | WARNING | `f"Cannot extend - not recording (state: {self.state.value})"` | ERROR | Wrong state |
| 247 | WARNING | `f"Cannot extend - would exceed maximum ({new_limit}s > {MAX_RECORDING_DURATION}s)"` | ERROR | Max reached |
| 473 | ERROR | `f"Error in monitoring thread: {e}"` | ERROR | Monitor error |
| 490-494 | ERROR | `f"Error in {callback_name} callback: {e}"` | ERROR | Callback errors |

---

## 4. STORAGE CONTROLLER
**File**: `storage/controllers/storage_controller.py`

### 4.1 Initialization & Lifecycle
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 82 | INFO | `"Storage controller initialized"` | LIFECYCLE | Init |
| 413 | INFO | `"Cleaning up storage controller"` | LIFECYCLE | Cleanup |
| 415 | INFO | `"Storage controller cleanup complete"` | LIFECYCLE | Cleanup done |

### 4.2 Video Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 121 | INFO | `f"Saved video to storage: {video.filename} (id={video.id})"` | OPERATION | Video saved |
| 149 | INFO | `f"Upload started: {video.filename}"` | OPERATION | Upload started |
| 175 | INFO | `f"Upload successful: {video.filename} → {youtube_id}"` | OPERATION | Upload success |
| 203 | WARNING | `f"Upload failed: {video.filename} (retry_count={video.retry_count})"` | OPERATION | Upload failed |
| 210 | ERROR | `f"Upload failed permanently: {video.filename} (max retries reached)"` | OPERATION | Upload exhausted |

### 4.3 Cleanup Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 293 | INFO | `f"Would cleanup {count} old videos"` | OPERATION | Dry run |
| 295 | INFO | `f"Cleaned up {count} old videos"` | OPERATION | Cleanup done |
| 354 | INFO | `f"🗑️ Storage cleanup: deleted {summary['total_deleted']} videos, freed {summary['space_freed_gb']:.2f} GB"` | OPERATION | Cleanup summary |

### 4.4 Errors
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 110 | ERROR | `"Cannot save recording: insufficient disk space"` | ERROR | Disk full |
| 131 | ERROR | `f"Failed to save recording: {e}"` | ERROR | Save failed |
| 153 | ERROR | `f"Failed to mark upload started: {e}"` | ERROR | DB error |
| 181 | ERROR | `f"Failed to mark upload success: {e}"` | ERROR | DB error |
| 218 | ERROR | `f"Failed to mark upload failed: {e}"` | ERROR | DB error |
| 301 | ERROR | `f"Cleanup failed: {e}"` | ERROR | Cleanup error |
| 320 | ERROR | `f"Failed to get cleanup summary: {e}"` | ERROR | Summary error |
| 373-405 | ERROR | `f"Error in {callback}_callback: {e}"` | ERROR | Callback errors |

---

## 5. LOCAL STORAGE (Implementation)
**File**: `storage/implementations/local_storage.py`

### 5.1 Initialization
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 76 | INFO | `f"Local storage initialized (base: {settings.STORAGE_BASE_PATH})"` | LIFECYCLE | Init |
| 86 | INFO | `"Storage system initialized and ready"` | LIFECYCLE | Ready |
| 385 | INFO | `"Cleaning up local storage"` | LIFECYCLE | Cleanup |
| 387 | INFO | `"Local storage cleanup complete"` | LIFECYCLE | Cleanup done |

### 5.2 File Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 125 | INFO | `f"Saved video file: {dest_path.name}"` | OPERATION | File saved |
| 156 | INFO | `f"Saved video metadata to database: {video.filename} (id={video.id})"` | OPERATION | DB saved |
| 210 | INFO | `f"Deleted video: {video.filename}"` | OPERATION | Video deleted |

### 5.3 Validation
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 249 | INFO | `f"⚠️ Corrupted video detected: {video.filename} - moved to failed/"` | OPERATION | Corruption detected |
| 291 | DEBUG | `f"Video validated successfully: {video.filename}"` | DEBUG | Valid video |

### 5.4 Cleanup
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 350 | INFO | `"No videos need cleanup"` | OPERATION | Nothing to clean |

### 5.5 Errors
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 284 | ERROR | `f"Failed to move corrupted video: {e}"` | ERROR | Move failed |
| 286 | ERROR | `f"Video validation failed: {video.filename} - {e}"` | ERROR | Validation error |

---

## 6. UPLOAD CONTROLLER
**File**: `upload/controllers/upload_controller.py`

### 6.1 Initialization
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 74 | WARNING | `"Uploader initialized but not available. Check authentication and network connection."` | ERROR | Not available |
| 79 | INFO | `"Upload Controller initialized"` | LIFECYCLE | Init |
| 253 | INFO | `"Upload Controller cleanup"` | LIFECYCLE | Cleanup |

### 6.2 Upload Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 118 | INFO | `f"Uploading video: {video_path}"` | OPERATION | Upload start |
| 119 | DEBUG | `f"Title: {title}, Playlist: {target_playlist}"` | DEBUG | Upload details |
| 132 | INFO | `f"✅ Upload successful: {result.video_id} ({result.upload_duration:.1f}s, {result.file_size / (1024 * 1024):.1f} MB)"` | OPERATION | Success (emoji) |
| 138 | ERROR | `f"❌ Upload failed: {result.error_message} (status: {result.status.value})"` | ERROR | Failed (emoji) |

### 6.3 Connection Testing
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 186 | INFO | `"Testing YouTube connection..."` | OPERATION | Test start |
| 192 | INFO | `"✅ Connection test passed"` | OPERATION | Test OK (emoji) |
| 194 | WARNING | `"❌ Connection test failed"` | ERROR | Test failed (emoji) |
| 199 | ERROR | `f"Connection test error: {e}"` | ERROR | Test error |

### 6.4 Settings
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 167 | WARNING | `f"Invalid timestamp format: {timestamp}. Expected: YYYY-MM-DD HH:MM:SS"` | ERROR | Format error |
| 244 | INFO | `f"Default playlist set to: {playlist_id}"` | OPERATION | Playlist changed |

---

## 7. YOUTUBE UPLOADER (Implementation)
**File**: `upload/implementations/youtube_uploader.py`

### 7.1 Initialization
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 85 | INFO | `"YouTube Uploader initialized"` | LIFECYCLE | Init |
| 103 | DEBUG | `"YouTube API service initialized"` | DEBUG | API ready |

### 7.2 Upload Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 154 | DEBUG | `f"Starting upload: {video_path} → '{title}'"` | DEBUG | Upload start |
| 190 | INFO | `f"✅ Video uploaded successfully: {video_id}"` | OPERATION | Success (emoji) |
| 232 | INFO | `f"Added video to playlist: {playlist_id}"` | OPERATION | Playlist add |
| 319 | INFO | `f"Upload progress: {progress}%"` | METRIC | Progress |

### 7.3 Connection Testing
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 422 | INFO | `"✅ YouTube API connection test successful"` | OPERATION | Test OK (emoji) |

### 7.4 Errors
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 248 | ERROR | `f"Upload failed: {e}"` | ERROR | Upload error |
| 262 | ERROR | `f"Upload interrupted: {error_msg}"` | ERROR | Interrupted |
| 276 | ERROR | `f"Upload error: {error_msg}"` | ERROR | Generic error |
| 325 | WARNING | `f"Resumable upload failed after {attempt}/{MAX_RETRIES}: {e.reason}"` | ERROR | Retry exhausted |
| 372 | WARNING | `f"Failed to add video to playlist: {e}"` | ERROR | Playlist failed |
| 426 | ERROR | `f"❌ YouTube API connection test failed: {e}"` | ERROR | Test failed (emoji) |

---

## 8. HARDWARE CONTROLLERS

### 8.1 Audio Controller
**File**: `hardware/controllers/audio_controller.py`

#### Initialization & Lifecycle
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 78 | INFO | `f"Audio Controller initialized (TTS: {type(self.tts).__name__}, Queue: {queue_enabled})"` | LIFECYCLE | Init |
| 395 | INFO | `"Cleaning up Audio Controller"` | LIFECYCLE | Cleanup |
| 406 | INFO | `"Audio Controller cleanup complete"` | LIFECYCLE | Cleanup done |

#### Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 125 | INFO | `f"Playing message: {message_key.value}"` | OPERATION | Message play |
| 146 | INFO | `f"Playing text: '{text[:50]}...'"` | OPERATION | Text play |
| 166 | INFO | `f"Cleared {cleared} pending messages"` | OPERATION | Queue cleared |
| 231 | INFO | `f"Volume set to {volume}"` | OPERATION | Volume changed |
| 250 | INFO | `f"Speech rate set to {rate} WPM"` | OPERATION | Rate changed |
| 295 | INFO | `"Starting audio test"` | OPERATION | Test start |
| 305 | INFO | `f"Testing: {message}"` | OPERATION | Testing message |
| 311 | INFO | `"Audio test complete"` | OPERATION | Test done |
| 323 | INFO | `"Testing all predefined messages"` | OPERATION | Test all start |
| 326 | INFO | `f"Testing: {message_key.value}"` | OPERATION | Testing key |
| 332 | INFO | `"All message tests complete"` | OPERATION | Test all done |

#### Warnings & Errors
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 92 | DEBUG | `f"TTS configured: rate={rate}WPM, volume={volume}, voice={voice}"` | DEBUG | Config |
| 96 | WARNING | `f"Could not configure TTS: {e}"` | ERROR | Config failed |
| 128 | ERROR | `f"Unknown message key: {message_key}: {e}"` | ERROR | Unknown key |
| 143 | WARNING | `"Empty text provided for speech"` | ERROR | Empty text |
| 233 | ERROR | `f"Failed to set volume: {e}"` | ERROR | Volume failed |
| 252 | ERROR | `f"Failed to set speech rate: {e}"` | ERROR | Rate failed |
| 404 | WARNING | `f"Error during TTS cleanup: {e}"` | ERROR | Cleanup error |

### 8.2 LED Controller
**File**: `hardware/controllers/led_controller.py`

#### Initialization
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 118 | INFO | `f"LED Controller initialized (GPIO: {type(self.gpio).__name__})"` | LIFECYCLE | Init |
| 342 | INFO | `"Cleaning up LED Controller"` | LIFECYCLE | Cleanup |
| 351 | INFO | `"LED Controller cleanup complete"` | LIFECYCLE | Cleanup done |

#### Pattern Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 136 | INFO | `f"Set pattern: {pattern.value}"` | OPERATION | Pattern set |
| 179 | INFO | `f"All LEDs off"` | OPERATION | All off |
| 195 | INFO | `f"LED test started"` | OPERATION | Test start |
| 204 | INFO | `f"Testing LED: {color.value}"` | OPERATION | Testing LED |
| 210 | INFO | `"LED test complete"` | OPERATION | Test done |
| 224 | INFO | `"Testing all patterns..."` | OPERATION | Test patterns |
| 227 | INFO | `f"Testing pattern: {pattern.value}"` | OPERATION | Testing pattern |
| 234 | INFO | `"Pattern test complete"` | OPERATION | Pattern test done |

#### Errors
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 160 | ERROR | `f"Error setting pattern {pattern.value}: {e}"` | ERROR | Pattern error |
| 162 | ERROR | `f"Failed to stop animation: {e}"` | ERROR | Stop failed |
| 347 | ERROR | `f"Error during LED cleanup: {e}"` | ERROR | Cleanup error |

### 8.3 Button Controller
**File**: `hardware/controllers/button_controller.py`

#### Initialization
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 138 | INFO | `f"Button Controller initialized (GPIO: {type(self.gpio).__name__}, debounce: {self.debounce_time}s)"` | LIFECYCLE | Init |
| 284 | INFO | `"Cleaning up Button Controller"` | LIFECYCLE | Cleanup |
| 290 | INFO | `"Button Controller cleanup complete"` | LIFECYCLE | Cleanup done |

#### Button Events
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 175 | DEBUG | `f"Button pressed (raw event)"` | DEBUG | Raw press |
| 181 | DEBUG | `f"Debounce: ignored press (too soon after last)"` | DEBUG | Debounced |
| 193 | DEBUG | `f"Button hold detected ({hold_time:.1f}s)"` | DEBUG | Hold detected |
| 199 | DEBUG | `f"Button released (held {duration:.2f}s)"` | DEBUG | Release |
| 203 | INFO | `f"LONG press detected ({duration:.2f}s)"` | OPERATION | Long press |
| 207 | INFO | `f"SHORT press detected ({duration:.2f}s)"` | OPERATION | Short press |

#### Test Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 229 | INFO | `"Testing button (press within 5 seconds)..."` | OPERATION | Test start |
| 247 | INFO | `f"✅ Button test PASSED - detected {press_type} press"` | OPERATION | Test OK (emoji) |
| 250 | WARNING | `"❌ Button test FAILED - no press detected"` | OPERATION | Test failed (emoji) |

#### Errors
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 221 | ERROR | `f"Error in button press handler: {e}"` | ERROR | Handler error |
| 287 | ERROR | `f"Error during button cleanup: {e}"` | ERROR | Cleanup error |

---

## 9. AUDIO SUBSYSTEM

### 9.1 Audio Queue
**File**: `hardware/audio/audio_queue.py`

#### Lifecycle
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 71 | INFO | `"Audio Queue initialized"` | LIFECYCLE | Init |
| 85 | WARNING | `"Worker already running"` | ERROR | Already running |
| 96 | DEBUG | `"Audio queue worker started"` | DEBUG | Worker start |
| 109 | DEBUG | `"Worker thread started"` | DEBUG | Thread start |
| 153 | DEBUG | `"Worker thread stopped"` | DEBUG | Thread stop |
| 362 | INFO | `"Stopping audio queue"` | LIFECYCLE | Stopping |
| 374 | INFO | `"Audio queue stopped"` | LIFECYCLE | Stopped |

#### Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 169 | DEBUG | `f"Speaking: '{text[:30]}...'"` | DEBUG | Speaking |
| 202 | DEBUG | `f"Queued message ({self.message_queue.qsize()} in queue): '{text[:30]}...'"` | DEBUG | Queued |
| 233 | INFO | `f"Cleared {cleared_count} queued messages"` | OPERATION | Queue cleared |

#### Errors
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 151 | ERROR | `f"Error in worker loop: {e}"` | ERROR | Worker error |
| 175 | ERROR | `f"Error speaking message: {e}"` | ERROR | Speech error |
| 196 | WARNING | `"Empty text provided, ignoring"` | ERROR | Empty text |
| 330 | ERROR | `f"Error waiting for idle: {e}"` | ERROR | Wait error |

### 9.2 Message Library
**File**: `hardware/audio/message_library.py`

#### Initialization
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 46 | INFO | `f"Message library initialized with {len(self._messages)} default messages"` | LIFECYCLE | Init |

#### Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 122 | INFO | `f"{action} message '{key.value}': {text}"` | OPERATION | Message set/updated |
| 148 | INFO | `f"Removed custom message '{key.value}'"` | OPERATION | Message removed |
| 195 | INFO | `"Message library reset to defaults"` | OPERATION | Reset |

---

## 10. STORAGE MANAGERS

### 10.1 File Manager
**File**: `storage/managers/file_manager.py`

#### Initialization
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 62 | INFO | `f"File manager initialized (base: {self.storage_base})"` | LIFECYCLE | Init |
| 74 | DEBUG | `"Storage directories created/verified"` | DEBUG | Dirs OK |

#### Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 138 | INFO | `f"Saved file: {filename} -> {destination_dir}/"` | OPERATION | File saved |
| 185 | INFO | `f"Moved file: {old_path.name} → {new_destination_dir}/"` | OPERATION | File moved |
| 209 | INFO | `f"Deleted file: {file_path.name}"` | OPERATION | File deleted |
| 309 | DEBUG | `f"Removed empty directory: {subdir}"` | DEBUG | Dir removed |

#### Errors
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 204 | WARNING | `f"File not found for deletion: {file_path}"` | ERROR | Not found |
| 311 | WARNING | `f"Error cleaning empty directories: {e}"` | ERROR | Cleanup error |

### 10.2 Space Manager
**File**: `storage/managers/space_manager.py`

#### Initialization
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 41 | INFO | `f"Space manager initialized (path: {self.storage_base})"` | LIFECYCLE | Init |

#### Space Checks
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 272 | ERROR | `f"Critical: Disk full! {free_gb:.2f}GB free (need {required_gb:.2f}GB)"` | ERROR | Disk full |
| 276 | WARNING | `f"Low disk space: {free_gb:.2f}GB free"` | ERROR | Low space |
| 280 | INFO | `f"Disk space OK: {free_gb:.2f}GB free ({free_percent:.1f}%)"` | METRIC | Space OK |

#### Errors
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 97 | WARNING | `f"Cannot calculate space: storage path does not exist: {self.storage_base}"` | ERROR | Path missing |
| 159 | WARNING | `f"Error calculating directory size: {e}"` | ERROR | Calc error |

### 10.3 Metadata Manager
**File**: `storage/managers/metadata_manager.py`

#### Initialization
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 67 | INFO | `f"Metadata manager initialized (db: {self.db_path})"` | LIFECYCLE | Init |
| 113 | DEBUG | `"Database schema initialized"` | DEBUG | Schema OK |
| 544 | DEBUG | `"Database connection closed"` | DEBUG | DB closed |

#### Database Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 209 | DEBUG | `f"Inserted video: {video.filename} (id={video.id})"` | DEBUG | Insert |
| 280 | DEBUG | `f"Updated video: {video.filename} (id={video.id})"` | DEBUG | Update |
| 418 | DEBUG | `f"Deleted video from database: id={video_id}"` | DEBUG | Delete |

#### Errors
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 546 | WARNING | `f"Error closing database: {e}"` | ERROR | Close error |

### 10.4 Cleanup Manager
**File**: `storage/managers/cleanup_manager.py`

#### Initialization
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 54 | INFO | `f"Cleanup manager initialized (policy: {settings.CLEANUP_POLICY})"` | LIFECYCLE | Init |

#### Cleanup Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 102 | INFO | `f"Cleanup check: {len(candidates)} candidates, {len(to_delete)} eligible for deletion"` | OPERATION | Check results |
| 119 | INFO | `f"[DRY RUN] Would delete: {video.filename}"` | OPERATION | Dry run |
| 122 | INFO | `f"Deleted: {video.filename}"` | OPERATION | Deleted |
| 139 | INFO | `f"Cleanup complete: deleted {deleted_count}/{len(to_delete)} videos, freed {space_freed_gb:.2f}GB"` | OPERATION | Cleanup summary |

#### Errors
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 125 | ERROR | `f"Failed to delete {video.filename}: {e}"` | ERROR | Delete failed |
| 129 | WARNING | `f"Insufficient space after cleanup: need {required_gb:.2f}GB, have {after_cleanup_gb:.2f}GB"` | ERROR | Still low |

---

## 11. STORAGE UTILS

### 11.1 Path Utils
**File**: `storage/utils/path_utils.py`

#### Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 68 | DEBUG | `f"Created directory: {path}"` | DEBUG | Dir created |

#### Errors
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 30 | ERROR | `f"Invalid path type: {type(path)}"` | ERROR | Type error |
| 34 | ERROR | `f"Path does not exist: {path}"` | ERROR | Not exist |
| 39 | WARNING | `f"Path is not absolute: {path}"` | ERROR | Not absolute |
| 62 | ERROR | `f"Path exists but is not a directory: {path}"` | ERROR | Not directory |
| 74 | ERROR | `f"Failed to create directory {path}: {e}"` | ERROR | Create failed |
| 217 | WARNING | `f"Error calculating directory size: {e}"` | ERROR | Calc error |

### 11.2 Validation Utils
**File**: `storage/utils/validation_utils.py`

#### Validation
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 102 | WARNING | `"ffprobe not available, skipping advanced validation"` | ERROR | No ffprobe |
| 106 | WARNING | `"ffprobe not found in PATH, skipping advanced validation"` | ERROR | Not in PATH |
| 109 | WARNING | `"ffprobe version check timeout"` | ERROR | Timeout |
| 136 | DEBUG | `f"ffprobe error for {file_path.name}: {error_msg}"` | DEBUG | Probe error |
| 157 | DEBUG | `f"Video validated successfully: {file_path.name}"` | DEBUG | Valid |
| 204 | WARNING | `f"Failed to get duration for {file_path.name}"` | ERROR | Duration failed |

#### Errors
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 166 | ERROR | `f"Error during ffmpeg validation: {e}"` | ERROR | Validation error |
| 221 | WARNING | `f"Error getting video duration: {e}"` | ERROR | Duration error |
| 293 | WARNING | `f"Error getting video info: {e}"` | ERROR | Info error |

---

## 12. FACTORIES & IMPLEMENTATIONS

### 12.1 Hardware Factory
**File**: `hardware/factory.py`

| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 75 | INFO | `"Creating Mock GPIO (forced)"` | LIFECYCLE | Mock forced |
| 81 | INFO | `"Creating Raspberry Pi GPIO (forced)"` | LIFECYCLE | Real forced |
| 91 | INFO | `"Creating Raspberry Pi GPIO (auto-detected)"` | LIFECYCLE | Auto real |
| 94 | WARNING | `"RPi.GPIO not available, using Mock GPIO"` | LIFECYCLE | Auto mock |
| 129 | INFO | `f"Creating {tts_name} TTS (forced by FORCE_TTS_ENGINE={tts_name})"` | LIFECYCLE | TTS forced |
| 137 | INFO | `"Creating pyttsx3 TTS (forced)"` | LIFECYCLE | TTS forced |
| 147 | INFO | `"Creating pyttsx3 TTS (auto-detected)"` | LIFECYCLE | Auto TTS |
| 150 | WARNING | `"pyttsx3 not available, using Mock TTS"` | LIFECYCLE | Auto mock |

### 12.2 Recording Factory
**File**: `recording/factory.py`

| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 52 | INFO | `"Creating Mock Capture (forced)"` | LIFECYCLE | Mock forced |
| 58 | INFO | `"Creating FFmpeg Capture (forced)"` | LIFECYCLE | FFmpeg forced |
| 68 | INFO | `"Creating FFmpeg Capture (auto-detected)"` | LIFECYCLE | Auto FFmpeg |
| 71 | WARNING | `"FFmpeg not available, using Mock Capture"` | LIFECYCLE | Auto mock |

### 12.3 Storage Factory
**File**: `storage/factory.py`

| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 55 | INFO | `"Creating Mock Storage (forced)"` | LIFECYCLE | Mock forced |
| 61 | INFO | `"Creating Local Storage"` | LIFECYCLE | Local storage |
| 81 | ERROR | `f"Storage availability check failed: {e}"` | ERROR | Check failed |

### 12.4 Upload Factory
**File**: `upload/factory.py`

| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 69 | INFO | `"Creating Mock Uploader (forced)"` | LIFECYCLE | Mock forced |
| 75 | INFO | `"Creating YouTube Uploader (forced)"` | LIFECYCLE | YouTube forced |
| 85 | INFO | `"Creating YouTube Uploader (auto-detected)"` | LIFECYCLE | Auto YouTube |
| 88 | WARNING | `"YouTube credentials not available, using Mock Uploader"` | LIFECYCLE | Auto mock |

### 12.5 Mock Implementations
**File**: `storage/implementations/mock_storage.py`

| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 53 | INFO | `"[MOCK] Storage initialized (simulation mode)"` | LIFECYCLE | Mock init |
| 58 | DEBUG | `f"[MOCK] {operation}"` | DEBUG | Mock operation |

**File**: `upload/implementations/mock_uploader.py`

| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 70 | INFO | `f"[MOCK] Mock Uploader initialized (success_rate={success_rate})"` | LIFECYCLE | Mock init |
| 96 | INFO | `f"[MOCK] 📤 Uploading: {title}"` | OPERATION | Mock upload (emoji) |
| 107 | DEBUG | `f"[MOCK] Simulating upload delay ({delay}s)..."` | DEBUG | Delay |
| 139 | INFO | `f"[MOCK] ✅ Upload successful: {video_id}"` | OPERATION | Mock success (emoji) |
| 153 | ERROR | `f"[MOCK] Upload failed: {e}"` | ERROR | Mock fail |
| 166 | ERROR | `f"[MOCK] File not found: {video_path}"` | ERROR | Not found |
| 213 | WARNING | `"[MOCK] Connection test failed (simulated)"` | ERROR | Mock test fail |
| 216 | INFO | `"[MOCK] ✅ Connection test successful"` | OPERATION | Mock test OK (emoji) |
| 239 | DEBUG | `"[MOCK] Upload history cleared"` | DEBUG | History cleared |

**File**: `hardware/implementations/mock_tts.py`

| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 50 | INFO | `f"[MOCK TTS] Initialized (mock delay: {self._speech_delay}s)"` | LIFECYCLE | Mock init |
| 62 | WARNING | `"[MOCK TTS] Empty text provided"` | ERROR | Empty |
| 66 | INFO | `f"[MOCK TTS] Speaking: '{text}'"` | OPERATION | Speaking |
| 80 | DEBUG | `f"[MOCK TTS] Configured: rate={rate}WPM, vol={volume}, voice={voice}"` | DEBUG | Config |
| 91 | INFO | `f"[MOCK TTS] Rate set to {rate} WPM"` | OPERATION | Rate |
| 99 | INFO | `f"[MOCK TTS] Volume set to {volume}"` | OPERATION | Volume |
| 104 | INFO | `f"[MOCK TTS] Voice set to {self._config['voice_id']}"` | OPERATION | Voice |
| 120 | DEBUG | `"[MOCK TTS] Cleanup called"` | DEBUG | Cleanup |
| 139 | DEBUG | `"[MOCK TTS] History cleared"` | DEBUG | History |

### 12.6 Real Implementations
**File**: `hardware/implementations/pyttsx3_tts.py`

| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 59 | INFO | `"pyttsx3 TTS engine configured"` | LIFECYCLE | Init |
| 77 | INFO | `f"Found French voice: {voice.name}"` | LIFECYCLE | Voice found |
| 82 | INFO | `f"Using default voice: {voices[0].name}"` | LIFECYCLE | Default voice |
| 88 | WARNING | `f"Could not initialize voice config: {e}"` | ERROR | Config failed |
| 139 | WARNING | `"Empty text provided for speech"` | ERROR | Empty |
| 189 | DEBUG | `f"Spoke: '{text[:30]}...'"` | DEBUG | Spoke |
| 219 | INFO | `f"Speech rate set to {rate} WPM"` | OPERATION | Rate |
| 235 | INFO | `f"Volume set to {volume}"` | OPERATION | Volume |
| 256 | INFO | `f"Voice set to: {voice_name}"` | OPERATION | Voice |
| 275 | ERROR | `f"Failed to get voices: {e}"` | ERROR | Voices error |
| 289 | DEBUG | `"TTS cleanup (nothing to clean with fresh engines)"` | DEBUG | Cleanup |

**File**: `recording/implementations/ffmpeg_capture.py`

| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 112 | INFO | `f"FFmpeg Capture initialized (device: {self.camera_device})"` | LIFECYCLE | Init |
| 149 | INFO | `f"Starting FFmpeg capture: {output_file.name}"` | OPERATION | Start |
| 183 | INFO | `f"FFmpeg process started (PID: {self._process.pid})"` | OPERATION | Started |
| 221 | INFO | `"Stopping FFmpeg capture..."` | OPERATION | Stop |
| 230 | INFO | `"FFmpeg process terminated"` | OPERATION | Terminated |
| 347 | INFO | `"Cleaning up FFmpeg Capture"` | LIFECYCLE | Cleanup |
| 358 | INFO | `"FFmpeg Capture cleanup complete"` | LIFECYCLE | Cleanup done |

---

## 13. OAUTH & AUTH
**File**: `upload/auth/oauth_manager.py`

### Initialization
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 76 | INFO | `"OAuth Manager initialized"` | LIFECYCLE | Init |

### Token Operations
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 118 | INFO | `"Access token expired, refreshing..."` | OPERATION | Refresh start |
| 121 | INFO | `"Access token refreshed successfully"` | OPERATION | Refresh done |
| 129 | DEBUG | `"Credentials loaded and validated"` | DEBUG | Loaded |
| 140 | DEBUG | `"Credentials saved to token file"` | DEBUG | Saved |
| 162 | DEBUG | `"Token expired, refreshing..."` | DEBUG | Refresh |
| 206 | INFO | `"Credentials revoked"` | OPERATION | Revoked |
| 253 | INFO | `f"Starting OAuth flow on port {port}..."` | OPERATION | OAuth start |
| 254 | INFO | `"A browser window will open for authentication"` | OPERATION | Browser opening |
| 262 | INFO | `f"✅ Authentication successful! Token saved to: {token_path}"` | OPERATION | Auth success (emoji) |

### Errors
| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| 132 | ERROR | `f"Failed to load credentials: {e}"` | ERROR | Load failed |
| 142 | WARNING | `f"Failed to save credentials: {e}"` | ERROR | Save failed |
| 210 | ERROR | `f"Failed to revoke credentials: {e}"` | ERROR | Revoke failed |
| 242 | ERROR | `"Google auth libraries not installed"` | ERROR | No libs |
| 266 | ERROR | `f"Authentication failed: {e}"` | ERROR | Auth failed |

---

## 14. SCRIPTS & UTILITIES

### 14.1 Setup YouTube Auth
**File**: `setup_youtube_auth.py`

This script has many INFO/ERROR logs for setup wizard - mostly user-facing messages with emojis (✅, ❌).

### 14.2 Quick Check Script
**File**: `scripts/quick_check.py`

Has test-oriented logs with emojis for visual feedback during testing.

### 14.3 Cleanup Orphaned DB Script
**File**: `scripts/cleanup_orphaned_db_entries.py`

Has structured summary logs with separators (===) and checkmarks (✓, ✗).

### 14.4 Watchdog
**File**: `watchdog.py`

| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| Various | INFO/ERROR | Service monitoring logs | HEALTH | Heartbeat checks |

### 14.5 Metrics Exporter
**File**: `metrics_exporter.py`

| Line | Level | Current Message | Type | Notes |
|------|-------|----------------|------|-------|
| Various | INFO | Prometheus metrics logs | METRIC | Metrics export |

---

## SUMMARY STATISTICS

### By Level
- **DEBUG**: ~50 statements (internal details, thread lifecycles, DB operations)
- **INFO**: ~300 statements (operations, state changes, lifecycle)
- **WARNING**: ~50 statements (recoverable issues, validations)
- **ERROR**: ~100 statements (failures, exceptions)
- **CRITICAL**: 0 statements (none used)

### By Type
- **LIFECYCLE**: Initialization, cleanup, thread start/stop (~80)
- **OPERATION**: Recording, upload, file ops, button presses (~150)
- **STATE**: State transitions, system status (~20)
- **ERROR**: Failures, exceptions, warnings (~150)
- **HEALTH**: Health checks, warnings, monitoring (~20)
- **METRIC**: Progress, statistics, counters (~30)
- **DEBUG**: Internal details, traces (~50)

### Emoji Usage
Currently used in ~30 log statements:
- ✅ (success)
- ❌ (failure)
- 📤 (upload)
- 🗑️ (cleanup)
- ⚠️ (warning)
- 📢 (announcement)
- 📹 (recording)

### Common Patterns
1. **Verbose filenames**: Many logs include `.name` or full paths
2. **Inconsistent formats**: Mix of `f"Action: {detail}"` and `f"{detail} action"`
3. **Redundant context**: Filename/ID repeated in multiple logs
4. **No structured fields**: All flat strings, no key=value pairs
5. **Hard to grep**: Inconsistent terminology (e.g., "stopped" vs "complete")

---

## RECOMMENDATIONS FOR REFACTORING

### 1. Standardize Log Formats
```python
# Current (inconsistent)
logger.info(f"Recording started: {file.name}")
logger.info("Starting recording session")
logger.info(f"Started recording to {file}")

# Proposed (consistent)
logger.info(f"Recording started | file={file.name}")
logger.info("Recording starting | session_init=true")
logger.info(f"Recording active | file={file.name} | duration={duration}s")
```

### 2. Add Context Fields
```python
# Current (no context)
logger.info("Upload successful")

# Proposed (with context)
logger.info(f"Upload complete | video_id={video_id} | size_mb={size} | duration_s={duration}")
```

### 3. Consistent Terminology
- **Start/Stop** vs **Starting/Stopping** vs **Started/Stopped**
- **Failed** vs **Error** vs **Failure**
- Pick one and stick to it

### 4. Remove Emojis (Optional)
Emojis are cute but:
- Not grep-friendly
- May break log parsers
- Not professional for production logs
- Consider removing or making configurable

### 5. Structured Logging (Future)
Consider structlog for:
- Automatic context propagation
- Key-value pairs
- Better filtering/searching
- JSON output option

### 6. Log Levels Review
- Many INFO could be DEBUG (internal state changes)
- Some WARNING could be INFO (expected conditions)
- Some ERROR might be WARNING (recoverable issues)

---

## NEXT STEPS

**Please review this inventory and annotate with your changes:**

1. Mark messages to **DELETE** (too verbose/redundant)
2. Mark messages to **CHANGE** (specify new format)
3. Mark messages to **COMBINE** (merge related logs)
4. Mark messages to **PROMOTE/DEMOTE** (level changes)
5. Specify any **PATTERNS** you want applied across all modules

Example annotation:
```
Line 108 | INFO | "Initializing Recorder Service..."
→ CHANGE: "RecorderService initializing"

Line 600 | INFO | f"Recording started: {self.current_output_file.name}"
→ CHANGE: f"Recording started | file={name} | duration={duration}s"
→ REMOVE EMOJI from line 848 (upload success)
```

I'll then implement all changes systematically!
