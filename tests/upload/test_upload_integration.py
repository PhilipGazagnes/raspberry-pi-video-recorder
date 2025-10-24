"""
Upload Module Integration Tests

Focused tests following CLAUDE.md: simplicity first, top priorities only.

Tests cover:
1. Mock uploader works correctly
2. Upload controller can be instantiated with mocks
3. Basic operations don't crash
4. Factory creates correct implementations
5. File validation works
"""

import os
import tempfile

import pytest

from upload.constants import UploadStatus

# Import controller
from upload.controllers.upload_controller import UploadController

# Import factory
from upload.factory import UploaderFactory, create_uploader

# Import implementations
from upload.implementations.mock_uploader import MockUploader

# Import interfaces and types

# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def temp_video_file():
    """Create a temporary video file for testing"""
    # Create a temp file with .mp4 extension and some content
    with tempfile.NamedTemporaryFile(
        suffix=".mp4",
        delete=False,
        mode="wb",
    ) as f:
        # Write enough data to pass MIN_VIDEO_FILE_SIZE (1 MB)
        f.write(b"0" * (2 * 1024 * 1024))  # 2 MB
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def mock_uploader():
    """Create a mock uploader with fast timing"""
    return MockUploader(simulate_timing=False)


# =============================================================================
# MOCK UPLOADER TESTS
# =============================================================================


class TestMockUploader:
    """Test mock uploader implementation"""

    def test_mock_uploader_initialization(self):
        """MockUploader initializes correctly"""
        uploader = MockUploader(simulate_timing=False)

        assert uploader.simulate_timing is False
        assert uploader.fail_rate == 0.0
        assert uploader.upload_history == []

    def test_mock_uploader_is_available(self):
        """MockUploader is always available"""
        uploader = MockUploader(simulate_timing=False)

        assert uploader.is_available() is True

    def test_mock_uploader_test_connection(self):
        """MockUploader connection test works"""
        uploader = MockUploader(simulate_timing=False)

        assert uploader.test_connection() is True

    def test_mock_uploader_get_quota(self):
        """MockUploader returns fake quota"""
        uploader = MockUploader(simulate_timing=False)

        quota = uploader.get_upload_quota_remaining()
        assert quota is not None
        assert quota > 0

    def test_mock_uploader_upload_success(self, temp_video_file):
        """MockUploader can upload video successfully"""
        uploader = MockUploader(simulate_timing=False)

        result = uploader.upload_video(
            video_path=temp_video_file,
            title="Test Video",
            description="Test description",
            tags=["test", "video"],
        )

        assert result.success is True
        assert result.video_id is not None
        assert result.video_id.startswith("mock_")
        assert result.status == UploadStatus.SUCCESS
        assert result.file_size > 0

    def test_mock_uploader_tracks_history(self, temp_video_file):
        """MockUploader tracks upload history"""
        uploader = MockUploader(simulate_timing=False)

        # Upload a video
        result = uploader.upload_video(
            video_path=temp_video_file,
            title="Test Video",
        )

        # Check history
        history = uploader.get_upload_history()
        assert len(history) == 1
        assert history[0]["video_id"] == result.video_id
        assert history[0]["title"] == "Test Video"

    def test_mock_uploader_invalid_file(self):
        """MockUploader validates file existence"""
        uploader = MockUploader(simulate_timing=False)

        result = uploader.upload_video(
            video_path="/nonexistent/file.mp4",
            title="Test Video",
        )

        assert result.success is False
        assert result.status == UploadStatus.INVALID_FILE

    def test_mock_uploader_unsupported_format(self):
        """MockUploader validates file format"""
        uploader = MockUploader(simulate_timing=False)

        # Create temp file with invalid extension
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"0" * (2 * 1024 * 1024))
            temp_path = f.name

        try:
            result = uploader.upload_video(
                video_path=temp_path,
                title="Test Video",
            )

            assert result.success is False
            assert result.status == UploadStatus.INVALID_FILE
        finally:
            os.unlink(temp_path)

    def test_mock_uploader_file_too_small(self):
        """MockUploader validates minimum file size"""
        uploader = MockUploader(simulate_timing=False)

        # Create tiny file (less than MIN_VIDEO_FILE_SIZE)
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"tiny")
            temp_path = f.name

        try:
            result = uploader.upload_video(
                video_path=temp_path,
                title="Test Video",
            )

            assert result.success is False
            assert result.status == UploadStatus.INVALID_FILE
        finally:
            os.unlink(temp_path)

    def test_mock_uploader_helper_methods(self, temp_video_file):
        """MockUploader helper methods work"""
        uploader = MockUploader(simulate_timing=False)

        # Upload
        uploader.upload_video(temp_video_file, "Test 1")

        # Test helpers
        assert uploader.was_uploaded(temp_video_file) is True
        assert uploader.get_last_upload()["title"] == "Test 1"

        # Clear history
        uploader.clear_history()
        assert len(uploader.get_upload_history()) == 0


# =============================================================================
# UPLOAD CONTROLLER TESTS
# =============================================================================


class TestUploadController:
    """Test upload controller"""

    def test_controller_initialization(self):
        """UploadController initializes correctly"""
        mock = MockUploader(simulate_timing=False)
        controller = UploadController(uploader=mock)

        assert controller.uploader == mock

    def test_controller_upload_video(self, temp_video_file):
        """UploadController can upload video"""
        mock = MockUploader(simulate_timing=False)
        controller = UploadController(uploader=mock)

        result = controller.upload_video(
            video_path=temp_video_file,
            timestamp="2025-10-24 12:30:45",
        )

        assert result.success is True
        assert result.video_id is not None

    def test_controller_formats_title(self, temp_video_file):
        """UploadController formats video title correctly"""
        mock = MockUploader(simulate_timing=False)
        controller = UploadController(uploader=mock)

        result = controller.upload_video(
            video_path=temp_video_file,
            timestamp="2025-10-24 12:30:45",
        )

        # Check that title was formatted
        last_upload = mock.get_last_upload()
        assert last_upload is not None
        assert "2025-10-24" in last_upload["title"]

    def test_controller_test_connection(self):
        """UploadController can test connection"""
        mock = MockUploader(simulate_timing=False)
        controller = UploadController(uploader=mock)

        assert controller.test_connection() is True

    def test_controller_is_ready(self):
        """UploadController can check if ready"""
        mock = MockUploader(simulate_timing=False)
        controller = UploadController(uploader=mock)

        assert controller.is_ready() is True


# =============================================================================
# FACTORY TESTS
# =============================================================================


class TestUploaderFactory:
    """Test uploader factory"""

    def test_factory_creates_mock(self):
        """Factory creates mock uploader"""
        uploader = UploaderFactory.create_uploader(mode="mock")

        assert isinstance(uploader, MockUploader)
        assert uploader.is_available() is True

    def test_factory_convenience_function(self):
        """Convenience create_uploader function works"""
        uploader = create_uploader(force_mock=True)

        assert isinstance(uploader, MockUploader)
        assert uploader.is_available() is True

    def test_factory_with_playlist_id(self):
        """Factory passes playlist_id correctly"""
        uploader = UploaderFactory.create_uploader(
            mode="mock",
            playlist_id="test_playlist_123",
        )

        assert isinstance(uploader, MockUploader)
        assert uploader.playlist_id == "test_playlist_123"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests for upload module"""

    def test_full_upload_workflow(self, temp_video_file):
        """Full upload workflow from factory to completion"""
        # Create uploader via factory
        uploader = create_uploader(force_mock=True)

        # Create controller
        controller = UploadController(uploader=uploader)

        # Test connection
        assert controller.test_connection() is True

        # Upload video
        result = controller.upload_video(
            video_path=temp_video_file,
            timestamp="2025-10-24 15:30:00",
        )

        # Verify result
        assert result.success is True
        assert result.video_id is not None
        assert result.status == UploadStatus.SUCCESS

    def test_controller_without_explicit_uploader(self, temp_video_file):
        """Controller works with auto-created uploader"""
        # Don't provide uploader - should auto-create
        controller = UploadController()

        # Should still work (will create mock or real YouTube based on env)
        assert controller.is_ready() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
