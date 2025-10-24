"""
Metadata Manager

Manages video metadata in SQLite database.
Single responsibility: Database operations only.
"""

import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from config.settings import METADATA_DB_NAME
from storage.constants import UploadStatus
from storage.interfaces.storage_interface import StorageError
from storage.models.video_file import VideoFile


class MetadataManager:
    """
    Manages video metadata in SQLite database.

    Responsibilities:
    - Create and maintain database schema
    - CRUD operations for video metadata
    - Query videos by various criteria

    Thread Safety:
    - Designed for multi-threaded use (main + background threads)
    - READ operations (select, list) are non-blocking and concurrent
    - WRITE operations (insert, update, delete) use threading.Lock
    - Lock pattern prevents concurrent writes while allowing concurrent reads
    - SQLite's database-level locking handles read/write conflicts
    """

    def __init__(self, storage_base: Path):
        """
        Initialize metadata manager.

        Args:
            storage_base: Base storage directory (database goes here)

        Thread Safety:
            Creates a write lock for thread-safe WRITE operations.
            READ operations (select, list) proceed without locking.
        """
        self.logger = logging.getLogger(__name__)
        self.db_path = storage_base / METADATA_DB_NAME
        self._connection: Optional[sqlite3.Connection] = None

        # Thread synchronization for write operations
        # WHY: Prevents concurrent INSERT/UPDATE/DELETE that could cause
        #   data corruption or "database is locked" errors
        # Context: RecordingSession runs monitoring in background thread,
        #   UploadManager updates metadata from background thread. Multiple
        #   threads could simultaneously write to database
        # Pattern: Lock is only held during actual database writes, not
        #   during reads. SQLite database-level locking handles read/write
        #   coordination. Lock is only for write serialization
        self._write_lock = threading.Lock()

        # Initialize database
        self._initialize_db()

        self.logger.info(f"Metadata manager initialized (db: {self.db_path})")

    def _initialize_db(self) -> None:
        """Create database and tables if they don't exist"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Create videos table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT UNIQUE NOT NULL,
                    filepath TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    duration_seconds INTEGER,
                    file_size_bytes INTEGER,
                    status TEXT NOT NULL,
                    upload_attempts INTEGER DEFAULT 0,
                    last_upload_attempt TEXT,
                    upload_error TEXT,
                    youtube_url TEXT,
                    quality TEXT DEFAULT 'valid',
                    validation_error TEXT
                )
            """,
            )

            # Create indexes for common queries
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_status
                ON videos(status)
            """,
            )

            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_created_at
                ON videos(created_at)
            """,
            )

            conn.commit()
            self.logger.debug("Database schema initialized")

        except sqlite3.Error as e:
            raise StorageError(f"Failed to initialize database: {e}") from e

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection (reuses existing or creates new)"""
        if self._connection is None:
            try:
                # WHY check_same_thread=False: Allows this SQLite connection to
                #   be used across multiple threads
                # Context: SQLite default is check_same_thread=True (raises
                #   error if different thread uses connection). This app may
                #   access metadata from main thread AND background
                #   upload/cleanup threads
                # Tradeoff: Safety vs flexibility - we disable Python's thread
                #   safety check, but SQLite itself handles concurrent access
                #   via database-level locks. Must ensure we don't have
                #   simultaneous writes (handled by serialize operations through
                #   single manager instance)
                # Risk: If multiple threads call write operations
                #   (INSERT/UPDATE/DELETE) simultaneously, SQLite will raise
                #   "database is locked" errors. Current design is safe because:
                #   1) Single MetadataManager instance (not creating multiple
                #      managers)
                #   2) Short-lived write transactions (commit immediately after
                #      each operation)
                #   3) Most operations are reads (SELECT), which SQLite handles
                #      concurrently
                # Alternative: Use a connection pool or thread-local
                #   connections, but adds complexity for minimal benefit in this
                #   single-database, low-concurrency scenario
                self._connection = sqlite3.connect(
                    str(self.db_path),
                    check_same_thread=False,  # Allow multi-threaded access
                )
                # Return rows as dictionaries
                self._connection.row_factory = sqlite3.Row
            except sqlite3.Error as e:
                raise StorageError(f"Failed to connect to database: {e}") from e

        return self._connection

    def insert_video(self, video: VideoFile) -> VideoFile:
        """
        Insert new video into database.

        Thread-safe: Uses lock to prevent concurrent inserts.

        Args:
            video: VideoFile object to insert

        Returns:
            VideoFile with id set

        Raises:
            StorageError: If insert fails
        """
        with self._write_lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                data = video.to_dict()

                cursor.execute(
                    """
                    INSERT INTO videos (
                        filename, filepath, created_at, updated_at,
                        duration_seconds, file_size_bytes, status,
                        upload_attempts, last_upload_attempt, upload_error,
                        youtube_url, quality, validation_error
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        data["filename"],
                        data["filepath"],
                        data["created_at"],
                        data["updated_at"],
                        data["duration_seconds"],
                        data["file_size_bytes"],
                        data["status"],
                        data["upload_attempts"],
                        data["last_upload_attempt"],
                        data["upload_error"],
                        data["youtube_url"],
                        data["quality"],
                        data["validation_error"],
                    ),
                )

                conn.commit()

                # Set the ID on the video object
                video.id = cursor.lastrowid

                self.logger.debug(f"Inserted video: {video.filename} (id={video.id})")
                return video

            except sqlite3.IntegrityError as e:
                raise StorageError(f"Video already exists: {video.filename}") from e
            except sqlite3.Error as e:
                raise StorageError(f"Failed to insert video: {e}") from e

    def update_video(self, video: VideoFile) -> None:
        """
        Update existing video in database.

        Thread-safe: Uses lock to prevent concurrent updates.

        Args:
            video: VideoFile with updated data

        Raises:
            StorageError: If update fails
        """
        with self._write_lock:
            if video.id is None:
                raise StorageError("Cannot update video without id")

            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                # Update timestamp
                video.updated_at = datetime.now()
                data = video.to_dict()

                cursor.execute(
                    """
                    UPDATE videos SET
                        filename = ?,
                        filepath = ?,
                        updated_at = ?,
                        duration_seconds = ?,
                        file_size_bytes = ?,
                        status = ?,
                        upload_attempts = ?,
                        last_upload_attempt = ?,
                        upload_error = ?,
                        youtube_url = ?,
                        quality = ?,
                        validation_error = ?
                    WHERE id = ?
                """,
                    (
                        data["filename"],
                        data["filepath"],
                        data["updated_at"],
                        data["duration_seconds"],
                        data["file_size_bytes"],
                        data["status"],
                        data["upload_attempts"],
                        data["last_upload_attempt"],
                        data["upload_error"],
                        data["youtube_url"],
                        data["quality"],
                        data["validation_error"],
                        video.id,
                    ),
                )

                conn.commit()

                if cursor.rowcount == 0:
                    raise StorageError(f"Video not found: id={video.id}")

                self.logger.debug(f"Updated video: {video.filename} (id={video.id})")

            except sqlite3.Error as e:
                raise StorageError(f"Failed to update video: {e}") from e

    def get_video(self, video_id: int) -> Optional[VideoFile]:
        """
        Get video by ID.

        Args:
            video_id: Database ID

        Returns:
            VideoFile or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
            row = cursor.fetchone()

            if row:
                return VideoFile.from_dict(dict(row))
            return None

        except sqlite3.Error as e:
            raise StorageError(f"Failed to get video: {e}") from e

    def get_video_by_filename(self, filename: str) -> Optional[VideoFile]:
        """
        Get video by filename.

        Args:
            filename: Video filename

        Returns:
            VideoFile or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM videos WHERE filename = ?", (filename,))
            row = cursor.fetchone()

            if row:
                return VideoFile.from_dict(dict(row))
            return None

        except sqlite3.Error as e:
            raise StorageError(f"Failed to get video by filename: {e}") from e

    def list_videos(
        self,
        status: Optional[UploadStatus] = None,
        limit: Optional[int] = None,
        order_by: str = "created_at DESC",
    ) -> List[VideoFile]:
        """
        List videos with optional filtering.

        Args:
            status: Filter by upload status
            limit: Maximum number of videos
            order_by: SQL ORDER BY clause

        Returns:
            List of VideoFile objects
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM videos"
            params: List[Union[str, int]] = []

            if status:
                query += " WHERE status = ?"
                params.append(status.value)

            query += f" ORDER BY {order_by}"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            # WHY use ? placeholders instead of f-strings: SQL injection
            #   prevention
            # Context: User input (or any dynamic data) must NEVER be
            #   concatenated directly into SQL
            # Tradeoff: Slightly more verbose than f-strings, but absolutely
            #   necessary for security
            # Risk: Using f-strings like f"WHERE status = '{status}'" is
            #   catastrophically dangerous:
            #   Example: If status = "'; DROP TABLE videos; --" it would
            #   execute the DROP!
            #   Parameterized queries (?) separate SQL structure from data
            #   values. Database driver automatically escapes values,
            #   preventing malicious SQL injection
            # NEVER DO THIS: cursor.execute(f"SELECT * FROM videos WHERE
            #   status = '{status}'")
            # ALWAYS DO THIS: cursor.execute("SELECT * FROM videos WHERE
            #   status = ?", (status,))
            # Note: order_by uses f-string (line 309) because it's internal
            #   constant, not user input. If order_by came from user, it would
            #   also need validation/whitelist
            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [VideoFile.from_dict(dict(row)) for row in rows]

        except sqlite3.Error as e:
            raise StorageError(f"Failed to list videos: {e}") from e

    def delete_video(self, video_id: int) -> None:
        """
        Delete video from database.

        Thread-safe: Uses lock to prevent concurrent deletes.

        Args:
            video_id: Database ID

        Raises:
            StorageError: If deletion fails
        """
        with self._write_lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                cursor.execute("DELETE FROM videos WHERE id = ?", (video_id,))
                conn.commit()

                if cursor.rowcount == 0:
                    raise StorageError(f"Video not found: id={video_id}")

                self.logger.debug(f"Deleted video from database: id={video_id}")

            except sqlite3.Error as e:
                raise StorageError(f"Failed to delete video: {e}") from e

    def get_videos_by_status(self, status: UploadStatus) -> List[VideoFile]:
        """
        Get all videos with specific status.

        Args:
            status: Upload status to filter by

        Returns:
            List of VideoFile objects
        """
        return self.list_videos(status=status)

    def get_retry_queue(self) -> List[VideoFile]:
        """
        Get videos eligible for upload retry.

        Returns:
            List of failed videos under retry limit
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Get failed videos that haven't exceeded retry limit
            from config.settings import MAX_UPLOAD_RETRIES

            cursor.execute(
                """
                SELECT * FROM videos
                WHERE status = ? AND upload_attempts < ?
                ORDER BY last_upload_attempt ASC
            """,
                (UploadStatus.FAILED.value, MAX_UPLOAD_RETRIES),
            )

            rows = cursor.fetchall()
            return [VideoFile.from_dict(dict(row)) for row in rows]

        except sqlite3.Error as e:
            raise StorageError(f"Failed to get retry queue: {e}") from e

    def get_old_uploaded_videos(self, days: int) -> List[VideoFile]:
        """
        Get uploaded videos older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            List of old uploaded VideoFile objects
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Calculate cutoff date
            from datetime import timedelta

            cutoff = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff.isoformat()

            cursor.execute(
                """
                SELECT * FROM videos
                WHERE status = ? AND created_at < ?
                ORDER BY created_at ASC
            """,
                (UploadStatus.COMPLETED.value, cutoff_str),
            )

            rows = cursor.fetchall()
            return [VideoFile.from_dict(dict(row)) for row in rows]

        except sqlite3.Error as e:
            raise StorageError(f"Failed to get old videos: {e}") from e

    def get_count_by_status(self) -> Dict[str, int]:
        """
        Get count of videos by status.

        Returns:
            Dictionary: {status: count}
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT status, COUNT(*) as count
                FROM videos
                GROUP BY status
            """,
            )

            rows = cursor.fetchall()
            return {row["status"]: row["count"] for row in rows}

        except sqlite3.Error as e:
            raise StorageError(f"Failed to get status counts: {e}") from e

    def get_total_count(self) -> int:
        """Get total number of videos in database"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as count FROM videos")
            row = cursor.fetchone()

            return row["count"] if row else 0

        except sqlite3.Error as e:
            raise StorageError(f"Failed to get total count: {e}") from e

    def cleanup(self) -> None:
        """Close database connection"""
        if self._connection:
            try:
                self._connection.close()
                self._connection = None
                self.logger.debug("Database connection closed")
            except sqlite3.Error as e:
                self.logger.warning(f"Error closing database: {e}")

    def __del__(self):
        """Destructor - ensure connection is closed"""
        self.cleanup()
