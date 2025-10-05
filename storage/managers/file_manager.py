"""
File Manager

Manages physical video file operations.
Single responsibility: File system operations only.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from storage.constants import (
    DIR_CORRUPTED,
    DIR_FAILED,
    DIR_PENDING,
    DIR_UPLOADED,
    VIDEO_FILENAME_PATTERN,
)
from storage.interfaces.storage_interface import StorageError


class FileManager:
    """
    Manages physical video file operations.

    Responsibilities:
    - Create directory structure
    - Save, move, delete files
    - Generate filenames
    - File size calculations
    """

    def __init__(self, storage_base: Path):
        """
        Initialize file manager.

        Args:
            storage_base: Base storage directory
        """
        self.logger = logging.getLogger(__name__)
        self.storage_base = Path(storage_base)

        # Directory paths
        self.pending_dir = self.storage_base / DIR_PENDING
        self.uploaded_dir = self.storage_base / DIR_UPLOADED
        self.failed_dir = self.storage_base / DIR_FAILED
        self.corrupted_dir = self.storage_base / DIR_CORRUPTED

        # Map directory names to paths
        self.dir_map = {
            DIR_PENDING: self.pending_dir,
            DIR_UPLOADED: self.uploaded_dir,
            DIR_FAILED: self.failed_dir,
            DIR_CORRUPTED: self.corrupted_dir,
        }

        # Create directories
        self._create_directories()

        self.logger.info(f"File manager initialized (base: {self.storage_base})")

    def _create_directories(self) -> None:
        """Create all required directories if they don't exist"""
        try:
            # Create base directory
            self.storage_base.mkdir(parents=True, exist_ok=True)

            # Create subdirectories
            for dir_path in self.dir_map.values():
                dir_path.mkdir(parents=True, exist_ok=True)

            self.logger.debug("Storage directories created/verified")

        except OSError as e:
            raise StorageError(f"Failed to create directories: {e}") from e

    def generate_filename(self, timestamp: Optional[datetime] = None) -> str:
        """
        Generate filename for new video.

        Args:
            timestamp: Recording timestamp (default: now)

        Returns:
            Filename string: recording_2025-10-04_143025.mp4

        Example:
            filename = file_manager.generate_filename()
            # Returns: recording_2025-10-04_143025.mp4
        """
        if timestamp is None:
            timestamp = datetime.now()

        return timestamp.strftime(VIDEO_FILENAME_PATTERN)

    def save_file(
        self,
        source_path: Path,
        destination_dir: str = DIR_PENDING,
        custom_filename: Optional[str] = None,
    ) -> Path:
        """
        Save file to storage.

        Args:
            source_path: Path to source file
            destination_dir: Target directory name (pending/uploaded/failed)
            custom_filename: Custom filename (default: auto-generate)

        Returns:
            Path to saved file

        Raises:
            StorageError: If save operation fails
        """
        if not source_path.exists():
            raise StorageError(f"Source file not found: {source_path}")

        try:
            # Get destination directory
            dest_dir = self.dir_map.get(destination_dir)
            if dest_dir is None:
                raise StorageError(f"Unknown destination directory: {destination_dir}")

            # Generate or use custom filename
            filename = custom_filename or self.generate_filename()
            dest_path = dest_dir / filename

            # Check if file already exists
            if dest_path.exists():
                raise StorageError(f"File already exists: {filename}")

            # Copy file
            shutil.copy2(source_path, dest_path)

            self.logger.info(f"Saved file: {filename} -> {destination_dir}/")
            return dest_path

        except (OSError, shutil.Error) as e:
            raise StorageError(f"Failed to save file: {e}") from e

    def move_file(
        self,
        source_path: Path,
        destination_dir: str,
    ) -> Path:
        """
        Move file to different directory.

        Args:
            source_path: Current file path
            destination_dir: Target directory name

        Returns:
            New file path

        Raises:
            StorageError: If move operation fails
        """
        if not source_path.exists():
            raise StorageError(f"Source file not found: {source_path}")

        try:
            # Get destination directory
            dest_dir = self.dir_map.get(destination_dir)
            if dest_dir is None:
                raise StorageError(f"Unknown destination directory: {destination_dir}")

            # Keep same filename
            dest_path = dest_dir / source_path.name

            # Check if file already exists at destination
            if dest_path.exists():
                # Generate unique filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = source_path.stem
                suffix = source_path.suffix
                dest_path = dest_dir / f"{stem}_{timestamp}{suffix}"

            # Move file
            shutil.move(str(source_path), str(dest_path))

            self.logger.info(
                f"Moved file: {source_path.name} -> {destination_dir}/",
            )
            return dest_path

        except (OSError, shutil.Error) as e:
            raise StorageError(f"Failed to move file: {e}") from e

    def delete_file(self, file_path: Path) -> None:
        """
        Delete file from storage.

        Args:
            file_path: Path to file to delete

        Raises:
            StorageError: If deletion fails
        """
        if not file_path.exists():
            self.logger.warning(f"File not found for deletion: {file_path}")
            return

        try:
            file_path.unlink()
            self.logger.info(f"Deleted file: {file_path.name}")

        except OSError as e:
            raise StorageError(f"Failed to delete file: {e}") from e

    def get_file_size(self, file_path: Path) -> int:
        """
        Get file size in bytes.

        Args:
            file_path: Path to file

        Returns:
            File size in bytes

        Raises:
            StorageError: If file not accessible
        """
        if not file_path.exists():
            raise StorageError(f"File not found: {file_path}")

        try:
            return file_path.stat().st_size
        except OSError as e:
            raise StorageError(f"Failed to get file size: {e}") from e

    def file_exists(self, filename: str, directory: Optional[str] = None) -> bool:
        """
        Check if file exists.

        Args:
            filename: Filename to check
            directory: Specific directory to check (None = check all)

        Returns:
            True if file exists
        """
        if directory:
            dir_path = self.dir_map.get(directory)
            if dir_path:
                return (dir_path / filename).exists()
            return False

        # Check all directories
        for dir_path in self.dir_map.values():
            if (dir_path / filename).exists():
                return True

        return False

    def list_files(self, directory: str, pattern: str = "*.mp4") -> list[Path]:
        """
        List files in directory.

        Args:
            directory: Directory name
            pattern: Glob pattern (default: *.mp4)

        Returns:
            List of file paths
        """
        dir_path = self.dir_map.get(directory)
        if dir_path is None:
            raise StorageError(f"Unknown directory: {directory}")

        try:
            return sorted(dir_path.glob(pattern))
        except OSError as e:
            raise StorageError(f"Failed to list files: {e}") from e

    def get_directory_size(self, directory: str) -> int:
        """
        Get total size of all files in directory.

        Args:
            directory: Directory name

        Returns:
            Total size in bytes
        """
        dir_path = self.dir_map.get(directory)
        if dir_path is None:
            raise StorageError(f"Unknown directory: {directory}")

        try:
            total_size = 0
            for file_path in dir_path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except OSError as e:
            raise StorageError(f"Failed to get directory size: {e}") from e

    def cleanup_empty_directories(self) -> None:
        """Remove empty subdirectories (not the main dirs)"""
        try:
            for dir_path in self.dir_map.values():
                for subdir in dir_path.rglob("*"):
                    if subdir.is_dir() and not any(subdir.iterdir()):
                        subdir.rmdir()
                        self.logger.debug(f"Removed empty directory: {subdir}")
        except OSError as e:
            self.logger.warning(f"Error cleaning empty directories: {e}")

    def validate_storage_writable(self) -> bool:
        """
        Test if storage is writable.

        Returns:
            True if writable, False otherwise
        """
        try:
            # Try to create and delete a test file
            test_file = self.storage_base / ".write_test"
            test_file.touch()
            test_file.unlink()
            return True
        except OSError:
            return False

    def get_storage_info(self) -> dict:
        """
        Get storage directory information.

        Returns:
            Dictionary with directory paths and status
        """
        return {
            "storage_base": str(self.storage_base),
            "pending_dir": str(self.pending_dir),
            "uploaded_dir": str(self.uploaded_dir),
            "failed_dir": str(self.failed_dir),
            "corrupted_dir": str(self.corrupted_dir),
            "writable": self.validate_storage_writable(),
            "exists": self.storage_base.exists(),
        }
