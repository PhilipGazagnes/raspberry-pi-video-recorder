---
  🔴 CRITICAL ISSUES

  1. Configuration Fragmentation (Violates Guidelines)

  Problem: Configuration is scattered across multiple locations:
  - config/settings.py - Main config file
  - storage/config.py - Storage-specific YAML config
  - hardware/constants.py - GPIO pins duplicated from settings.py
  - Each module has its own constants.py

  Guideline Violation:
  "ALL config in config/settings.py (GPIO pins, durations, paths)"
  "Modules import from config.settings, never use os.getenv() directly"

  Impact:
  - GPIO pins defined in BOTH config/settings.py (lines 2-5) AND hardware/constants.py (lines 23-26)
  - Creates single point of failure if they diverge
  - Storage module uses separate YAML system instead of central config

  Recommendation:
  1. Consolidate ALL config into config/settings.py
  2. Remove storage/config.py YAML system
  3. Remove duplicate GPIO pin definitions from hardware/constants.py
  4. Keep only non-configurable constants (like timing patterns, API URLs) in module constants.py files

  ---
  2. Domain-Specific Logic in Multiple Places

  Problem: "Boxing" terminology appears in upload module:

  upload/constants.py:58
  VIDEO_TITLE_PREFIX = "Boxing Session"

  upload/controllers/upload_controller.py:152
  # Returns: "Boxing Session 2025-10-12 18:30:45"

  Guideline Violation:
  "NEVER hardcode domain logic (no 'boxing', 'training', etc.)"
  "Configuration-driven behavior"

  Recommendation:
  - Move VIDEO_TITLE_PREFIX to config/settings.py
  - Make it configurable: SESSION_TITLE_PREFIX = "Session" (generic)
  - Document that users can customize for their domain

  ---
  3. Hardcoded Credentials in Settings

  config/settings.py:18-20
  # YouTube Configuration
  YOUTUBE_CLIENT_ID = "your_client_id"
  YOUTUBE_CLIENT_SECRET = "your_client_secret"

  Guideline Violation:
  "ALL secrets in .env at root (API keys, credentials)"
  "Never hardcode credentials"

  Recommendation:
  - Remove these from settings.py immediately
  - Document in README that these must be in .env
  - Add .env.example file with placeholder values

  ---
  ⚠️ ARCHITECTURAL IMPROVEMENTS

  4. Storage Module Config Complexity

  Problem: storage/config.py is 266 lines implementing YAML-based configuration with:
  - File I/O
  - Default creation
  - Validation
  - Property accessors

  Issues:
  - Adds unnecessary complexity (violates "Radical Simplicity")
  - Different pattern than other modules (inconsistent)
  - YAML dependency for just storage module
  - Saves config files at runtime (side effects)

  Recommendation:
  - Delete storage/config.py entirely
  - Move all storage settings to config/settings.py
  - Use simple Python constants (no runtime file I/O)
  - Reduces codebase by ~250 lines

  ---
  5. Missing Type Hints in Some Functions

  upload/controllers/upload_controller.py:144
  def _format_video_title(self, timestamp: str) -> str:
  Comment says returns string with format, but no validation of timestamp type safety.

  storage/controllers/storage_controller.py:290
  def get_cleanup_summary(self) -> dict:  # Should be Dict[str, Any]

  Guideline Violation:
  "Type hints everywhere"

  Recommendation:
  - Use Dict[str, Any] instead of dict
  - Use List[VideoFile] instead of implicit list types
  - Import from typing for Python 3.8 compatibility

  ---
  6. Inconsistent Error Handling Documentation

  recording/controllers/camera_manager.py:108-130
  - Docstring says "Raises: CaptureError"
  - But also catches general Exception and returns False
  - Inconsistent whether errors are raised or returned as bool

  Recommendation:
  - Standardize: Controllers should catch and return bool
  - Interfaces should raise specific exceptions
  - Document this pattern in CLAUDE.md

  ---
  📚 CODE QUALITY IMPROVEMENTS

  7. Missing Educational Comments in Complex Areas

  Good Example (hardware/controllers/button_controller.py:163-178):
  """
  GPIO interrupt handler - called automatically on button press.

  This runs in a separate thread created by the GPIO library.
  We need to be thread-safe here!
  ...

  Missing (storage/managers/metadata_manager.py:98-100):
  self._connection = sqlite3.connect(
      str(self.db_path),
      check_same_thread=False,  # Allow multi-threaded access  ← needs explanation WHY
  )

  Guideline:
  "Educational comments - explain WHY"

  Recommendation:
  Add comments explaining:
  - Why check_same_thread=False is needed (asyncio/threading context)
  - SQLite connection pooling strategy
  - Thread safety implications

  ---
  8. Long Functions (>50 Lines)

  storage/controllers/storage_controller.py:316-337
  get_status() method is manageable but could be cleaner.

  storage/managers/metadata_manager.py:109-165
  insert_video() is 57 lines with SQL construction.

  Guideline:
  "Keep functions < 50 lines"

  Recommendation:
  - Extract SQL query building to separate methods
  - Use query builder pattern for complex SQL

  ---
  9. Destructor Anti-Pattern

  Multiple files have __del__ methods that call cleanup:

  def __del__(self):
      """Destructor - ensure cleanup"""
      self.cleanup()

  Problem:
  - __del__ is unreliable in Python (may never be called)
  - Can cause issues with circular references
  - Not guaranteed order of execution

  Recommendation:
  - Remove all __del__ methods
  - Use context managers (__enter__/__exit__) instead
  - Document that users must call cleanup() explicitly or use with statement

  ---
  10. Module Constants Should Reference Central Config

  hardware/constants.py:23-26
  GPIO_BUTTON_PIN = 18
  GPIO_LED_GREEN = 12
  GPIO_LED_ORANGE = 16
  GPIO_LED_RED = 20

  These duplicate config/settings.py!

  Recommendation:
  # hardware/constants.py
  from config.settings import (
      GPIO_BUTTON_PIN,
      GPIO_LED_GREEN,
      GPIO_LED_ORANGE,
      GPIO_LED_RED
  )

  This creates single source of truth while maintaining import convenience.

  ---
  🎯 DEPENDENCY INJECTION IMPROVEMENTS

  11. Storage Module Instantiates Dependencies

  storage/controllers/storage_controller.py:302
  from storage.managers.cleanup_manager import CleanupManager
  cleanup_mgr = CleanupManager(self.config)

  Problem: Creating dependency inside method rather than injecting.

  Recommendation:
  - Inject CleanupManager in constructor
  - Pass as optional parameter with default creation
  - Improves testability

  ---
  📖 DOCUMENTATION IMPROVEMENTS

  12. Missing Module-Level Docstrings

  Several __init__.py files are empty or minimal.

  Recommendation:
  Add module-level documentation to each __init__.py:
  """
  Storage Module

  Handles video file storage with:
  - Multi-directory organization (pending/uploaded/failed)
  - SQLite metadata tracking
  - Space management and cleanup
  - Upload status tracking

  Main entry point: StorageController
  """

  ---
  13. Constants Files Need Better Structure Comments

  The constants files are good but could benefit from clearer section markers.

  Recommendation:
  Add more context to section headers explaining design decisions:
  # =============================================================================
  # GPIO PIN CONFIGURATION
  # =============================================================================
  # These are imported from config.settings for convenience.
  # NEVER modify here - change in config/settings.py instead!

  ---
  🧪 TESTING & RELIABILITY

  14. Health Check Uses hasattr for Mock Detection

  recording/controllers/camera_manager.py:258-260
  if hasattr(self.capture, "_crashed"):
      crashed = self.capture._crashed

  Problem: Production code checking for test-specific attributes.

  Recommendation:
  - Add get_crash_status() method to interface
  - Mock implementations can override
  - Real implementations return False
  - Cleaner separation of concerns

  ---
  15. SQLite Connection Not Thread-Safe Pattern

  storage/managers/metadata_manager.py:95-107
  Uses check_same_thread=False but doesn't implement connection pooling or locking.

  Risk: Potential race conditions with concurrent access.

  Recommendation:
  - Document thread safety requirements
  - Add threading.Lock for write operations
  - Or use connection-per-thread pattern
  - Add educational comment explaining the choice

  ---
  📊 STATISTICS & PRIORITIES

  By Priority:

  1. Critical (Do First): Issues #1, #2, #3 - Configuration & domain logic
  2. High (Architecture): Issues #4, #6, #9, #11 - Structural improvements
  3. Medium (Quality): Issues #5, #7, #8, #10 - Code quality & consistency
  4. Low (Polish): Issues #12, #13, #14, #15 - Documentation & edge cases

  By Module:

  - Config System: 3 critical issues
  - Storage: 4 issues (config complexity, type hints, SQL, threading)
  - Upload: 2 issues (domain logic, type hints)
  - Recording: 2 issues (error handling, health check)
  - Hardware: 1 issue (constants duplication)
  - Cross-cutting: 4 issues (destructors, docstrings, comments, DI)

  Impact Estimate:

  - Fixing all issues: ~500 lines removed (storage/config.py)
  - ~200 lines modified (consolidating config)
  - Net result: Smaller, cleaner codebase ✅

  ---
  ✅ WHAT'S WORKING WELL

  Great job on these aspects:
  1. SOLID Principles: Clear separation of interfaces/implementations
  2. Dependency Injection: Controllers accept injected dependencies
  3. Factory Pattern: Clean create_*() functions for each module
  4. Mock Implementations: Every interface has testable mock
  5. Consistent Structure: All modules follow same pattern
  6. Type Hints: Generally good coverage
  7. Logging: Comprehensive throughout
  8. Educational Comments: Hardware module is exemplary

  ---
