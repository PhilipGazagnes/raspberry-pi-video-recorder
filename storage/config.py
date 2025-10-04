"""
Storage Configuration Handler

Manages YAML configuration file for storage settings.
Provides defaults and validation.
"""

import logging
from pathlib import Path
from typing import Any, Dict

import yaml

from storage.constants import (
    CLEANUP_INTERVAL_SECONDS,
    DEFAULT_STORAGE_BASE,
    LOW_SPACE_WARNING_BYTES,
    MAX_UPLOAD_RETRIES,
    MAX_UPLOADED_VIDEOS,
    MIN_FREE_SPACE_BYTES,
    MIN_VIDEO_SIZE_BYTES,
    RETRY_DELAY_SECONDS,
    UPLOADED_RETENTION_DAYS,
)


class StorageConfig:
    """
    Storage configuration with YAML file support.

    Reads from config/storage.yaml if it exists,
    otherwise uses defaults from constants.py.

    Usage:
        config = StorageConfig()
        base_path = config.storage_base_path
        min_space = config.min_free_space_bytes
    """

    # Default config file location
    DEFAULT_CONFIG_PATH = Path("config/storage.yaml")

    def __init__(self, config_path: Path = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to YAML config file (None = use default)
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH

        # Load configuration (defaults + file overrides)
        self._config = self._load_config()

        self.logger.info(f"Storage config loaded from {self.config_path}")

    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration values from constants"""
        return {
            # Paths
            'storage_base_path': str(DEFAULT_STORAGE_BASE),

            # Storage limits
            'max_uploaded_videos': MAX_UPLOADED_VIDEOS,
            'uploaded_retention_days': UPLOADED_RETENTION_DAYS,
            'min_free_space_bytes': MIN_FREE_SPACE_BYTES,
            'low_space_warning_bytes': LOW_SPACE_WARNING_BYTES,

            # Upload retry
            'max_upload_retries': MAX_UPLOAD_RETRIES,
            'retry_delay_seconds': RETRY_DELAY_SECONDS,

            # Validation
            'min_video_size_bytes': MIN_VIDEO_SIZE_BYTES,
            'enable_ffmpeg_validation': True,

            # Cleanup
            'cleanup_interval_seconds': CLEANUP_INTERVAL_SECONDS,
            'auto_cleanup_enabled': True,
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file or use defaults"""
        # Start with defaults
        config = self._get_defaults()

        # Try to load from file
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    file_config = yaml.safe_load(f) or {}

                # Merge file config with defaults (file overrides defaults)
                config.update(file_config)

                self.logger.info(f"Loaded config from {self.config_path}")

            except Exception as e:
                self.logger.warning(
                    f"Failed to load config from {self.config_path}: {e}. "
                    f"Using defaults."
                )
        else:
            self.logger.info(
                f"Config file not found at {self.config_path}. "
                f"Using defaults. Creating default config file..."
            )
            # Create default config file
            self._save_config(config)

        # Validate configuration
        self._validate_config(config)

        return config

    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration values"""
        # Validate paths
        storage_path = Path(config['storage_base_path'])
        if not storage_path.is_absolute():
            raise ValueError(
                f"storage_base_path must be absolute path: {storage_path}"
            )

        # Validate numeric values
        if config['min_free_space_bytes'] < 0:
            raise ValueError("min_free_space_bytes cannot be negative")

        if config['max_upload_retries'] < 0:
            raise ValueError("max_upload_retries cannot be negative")

        if config['uploaded_retention_days'] < 0:
            raise ValueError("uploaded_retention_days cannot be negative")

        # Warning thresholds should be higher than minimums
        if config['low_space_warning_bytes'] < config['min_free_space_bytes']:
            self.logger.warning(
                "low_space_warning_bytes is less than min_free_space_bytes. "
                "This may cause unexpected behavior."
            )

    def _save_config(self, config: Dict[str, Any] = None) -> None:
        """Save configuration to YAML file"""
        if config is None:
            config = self._config

        try:
            # Create config directory if it doesn't exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write YAML file with nice formatting
            with open(self.config_path, 'w') as f:
                yaml.dump(
                    config,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    indent=2
                )

            self.logger.info(f"Config saved to {self.config_path}")

        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")

    # =========================================================================
    # PROPERTY ACCESSORS
    # =========================================================================
    # These provide type-safe access to config values

    @property
    def storage_base_path(self) -> Path:
        """Get storage base directory as Path object"""
        return Path(self._config['storage_base_path'])

    @property
    def max_uploaded_videos(self) -> int:
        """Maximum number of videos to keep in uploaded directory"""
        return self._config['max_uploaded_videos']

    @property
    def uploaded_retention_days(self) -> int:
        """How many days to keep uploaded videos"""
        return self._config['uploaded_retention_days']

    @property
    def min_free_space_bytes(self) -> int:
        """Minimum free space required to start recording"""
        return self._config['min_free_space_bytes']

    @property
    def low_space_warning_bytes(self) -> int:
        """Threshold for low space warning"""
        return self._config['low_space_warning_bytes']

    @property
    def max_upload_retries(self) -> int:
        """Maximum number of upload retry attempts"""
        return self._config['max_upload_retries']

    @property
    def retry_delay_seconds(self) -> int:
        """Delay between retry attempts"""
        return self._config['retry_delay_seconds']

    @property
    def min_video_size_bytes(self) -> int:
        """Minimum valid video file size"""
        return self._config['min_video_size_bytes']

    @property
    def enable_ffmpeg_validation(self) -> bool:
        """Whether to use ffmpeg for video validation"""
        return self._config['enable_ffmpeg_validation']

    @property
    def cleanup_interval_seconds(self) -> int:
        """How often to run cleanup task"""
        return self._config['cleanup_interval_seconds']

    @property
    def auto_cleanup_enabled(self) -> bool:
        """Whether automatic cleanup is enabled"""
        return self._config['auto_cleanup_enabled']

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any, save: bool = True) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: New value
            save: If True, save to file immediately
        """
        self._config[key] = value

        if save:
            self._save_config()

    def reload(self) -> None:
        """Reload configuration from file"""
        self._config = self._load_config()
        self.logger.info("Configuration reloaded")

    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary"""
        return self._config.copy()

    def __repr__(self) -> str:
        """Human-readable representation"""
        return f"StorageConfig(path={self.config_path})"
