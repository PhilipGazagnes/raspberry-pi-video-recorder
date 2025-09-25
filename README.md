# Raspberry Pi Video Recorder

A Python service for recording videos on Raspberry Pi with hardware button control.

## Development Setup

This project uses modern Python development tools for code quality and consistency.

### Prerequisites

- Python 3.8 or higher
- Virtual environment (automatically created)

### Installation

1. Clone the repository and navigate to the project directory
2. The Python virtual environment will be automatically configured when you open the project in VS Code

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

### Project Structure

```
raspberry-pi-video-recorder/
├── recorder_service.py       # Main service coordinator
├── core/                     # Core state management
│   ├── __init__.py
│   └── state_machine.py      # State machine logic
├── hardware/                 # Hardware control modules
│   ├── __init__.py
│   └── button_controller.py  # Button handling
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # Development dependencies
├── pyproject.toml           # Tool configurations
└── lint.sh                 # Manual linting script
```
