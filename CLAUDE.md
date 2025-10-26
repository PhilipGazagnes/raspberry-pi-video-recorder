# Raspberry Pi Video Recorder - Development Guidelines

## Project Vision

Generic, production-ready video recording system for Raspberry Pi. Domain-agnostic and reusable - the boxing club is just the first customer.

**Developer Context**: Learning project for Python/Raspberry Pi. Code should teach through clear explanations.

## Core Principles

### 1. SOLID Architecture
- Single Responsibility per module
- Dependency Inversion: depend on protocols, not implementations
- Modules should compose in unexpected ways

### 2. Radical Simplicity
- Smallest possible codebase
- No over-engineering
- Delete before you add

### 3. Generic Design
- NEVER hardcode domain logic (no "boxing", "training", etc.)
- Configuration-driven behavior
- Modules work standalone or in different systems

### 4. Production Quality
- Type hints everywhere
- Comprehensive error handling
- Testing without hardware dependencies
- Educational comments for Python/RPi patterns

## Configuration

**ALL config in `config/settings.py`** (GPIO pins, durations, paths)
**ALL secrets in `.env` at root** (API keys, credentials)
**Modules import from `config.settings`**, never use `os.getenv()` directly

## Error Handling Pattern

**Three-layer strategy**:

### 1. Interfaces (Contracts)
Define what exceptions can be raised or what is returned. Interface docstrings are the contract:

```python
class VideoCaptureInterface(Protocol):
    def start_capture(self, output_file: Path, duration: Optional[float]) -> bool:
        """Start video capture.

        Returns:
            True if capture started successfully, False otherwise.

        Raises:
            CaptureError: If camera hardware initialization fails
        """

    def stop_capture(self) -> bool:
        """Stop video capture.

        Returns:
            True if stopped successfully, False if not capturing.
        """
```

### 2. Controllers (Orchestrators)
Controllers are safe wrappers - they **catch exceptions and return safe values**, never re-raise:

```python
class CameraManager:
    def start_recording(self, output_file: Path, duration: Optional[float]) -> bool:
        """Start recording video.

        Returns:
            True if recording started, False otherwise.
            All errors are caught, logged, and converted to False return.
        """
        try:
            success = self.capture.start_capture(output_file, duration)
            return success
        except CaptureError as e:
            self.logger.error(f"Camera error: {e}")
            return False  # Convert exception to safe return
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return False
```

### 3. Implementations (Concrete)
Implementations match their interface contract - raise exceptions as documented or return values as specified:

```python
class FFmpegCapture(VideoCaptureInterface):
    def start_capture(self, output_file: Path, duration: Optional[float]) -> bool:
        """Matches interface contract."""
        if not self.is_available():
            raise CameraNotFoundError("Camera not found")  # ✓ Documented in interface

        if self.is_capturing():
            raise CameraBusyError("Already capturing")  # ✓ Documented in interface

        try:
            # Actual FFmpeg startup
            return True
        except Exception as e:
            raise CaptureError(f"Capture failed: {e}")  # ✓ Wrap in documented exception
```

**Key Rule**:
- **Controllers catch and convert** exceptions to safe returns
- **Implementations raise** documented exceptions
- **Interfaces document** what happens
- **Never have contradictory documentation** - docstring must match code behavior

## Code Style

**Tools**: Black (88 chars) + isort + Ruff + mypy. Run `./lint.sh` before commits.

**Type everything**:
```python
def process_recording(session: RecordingSession, duration: int) -> UploadResult:
    """Process and upload completed recording.

    Raises:
        StorageError: If disk space insufficient
        UploadError: If upload fails after retries
    """
```

**Educational comments** - explain WHY, but MUST pass linting:
- Python/RPi patterns
- Hardware interactions (GPIO, threading)
- Non-obvious design decisions
- **CRITICAL**: Keep comment lines ≤ 88 characters (wrap if needed)
- Format: Use multiple lines instead of one long line

```python
# WHY dual debouncing (hardware + software)?
# Context: Switches bounce ~20ms - need filters
#   Hardware: Electrical noise filter (GPIO library)
#   Software: Safety net for missed bounces
# Tradeoff: Lose very fast presses (<50ms), ok for humans
time_since_last = current_time - self.last_press_time
if time_since_last < self.debounce_time:
    return  # Bounce detected, ignore
```

**Dependency injection**:
```python
class RecordingService:
    def __init__(self, camera: CameraInterface, storage: StorageInterface):
        self.camera = camera
        self.storage = storage
```

## Module Public API

**Every module MUST define a clear public API in `__init__.py`**:

```python
"""
Module Name

Brief description of module purpose.

Public API:
    - MainController: Primary interface
    - create_something: Factory function
    - SomeInterface: Contract definition
    - SomeError: Custom exceptions

Usage:
    from module import MainController

    controller = MainController()
    result = controller.do_something()
"""

from module.submodule import MainController, SomeInterface
from module.factory import create_something
from module.exceptions import SomeError

__all__ = [
    "MainController",
    "create_something",
    "SomeInterface",
    "SomeError",
]
```

**Public API Rules**:
- **ALWAYS import from module's public API**, never from submodules
  - ✅ `from hardware import create_gpio`
  - ❌ `from hardware.factory import create_gpio`
- **Export only what users need** - interfaces, controllers, factories, errors
- **Keep internal implementations private** - don't export implementation classes
- **Document usage** - show common import pattern in module docstring
- **Use `__all__`** - explicit is better than implicit

## Module Design Checklist

Before creating/modifying modules:
1. Single, clear responsibility?
2. Works independently?
3. Dependencies injected?
4. Testable without hardware?
5. Any domain-specific logic? (extract it)
6. **Public API defined in `__init__.py`?**
7. **All imports use public API?**

## Testing

- Unit tests: pure logic, mocked dependencies
- Integration tests: multi-component workflows
- Hardware simulation: mock GPIO/camera for CI/CD

**Keep in mind**: Simplicity. Think what top priority tests are needed and stick to that.

## Critical Rules

❌ **Never**:
- Hardcode domain terms or credentials
- Skip type hints or error handling
- Mix hardware logic with business logic
- Commit with linting errors - `./lint.sh` MUST pass with zero errors

✅ **Always**:
- Inject dependencies
- Keep functions < 50 lines
- Put config in `config/`, secrets in `.env`
- Add educational comments for complex patterns
- Keep ALL comment lines ≤ 88 characters (wrap, don't skip comments)
- Test before committing - `pytest` must pass with all tests green

## File Organization

```
config/     # All settings
core/       # State machine, events
hardware/   # GPIO, button, LED, audio
recording/  # Camera, sessions
upload/     # YouTube API
storage/    # File management
```

---

**Remember**: Every line is maintenance liability. Keep it tight, modular, and generic.
