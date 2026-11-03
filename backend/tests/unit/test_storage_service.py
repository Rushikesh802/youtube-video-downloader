"""Unit tests for StorageService."""
from datetime import datetime, timezone
import os
import tempfile
from unittest.mock import MagicMock
from botocore.exceptions import ClientError, EndpointConnectionError
import pytest

from app.services.storage_service import StorageService, DEFAULT_TRANSFER_CONFIG


@pytest.fixture
def storage():
    """Create fresh StorageService instance for testing."""
    return StorageService()


def test_generate_object_key(storage):
    """Object key must follow downloads/{user_id}/{year}/{month:02d}/{job_id}.{format}."""
    fixed_dt = datetime(2026, 11, 3, 15, 30, 0, tzinfo=timezone.utc)
    key = storage.generate_object_key(
        user_id="user-123",
        job_id="job-456",
        format_str=".mp4",
        timestamp=fixed_dt,
    )
    assert key == "downloads/user-123/2026/11/job-456.mp4"

    # Test without leading dot
    key2 = storage.generate_object_key(
        user_id="user-abc",
        job_id="job-xyz",
        format_str="webm",
        timestamp=fixed_dt,
    )
    assert key2 == "downloads/user-abc/2026/11/job-xyz.webm"


def test_upload_missing_file_raises(storage):
    """Uploading non-existent file must raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        storage.upload_file("/non/existent/file.mp4", "test_key.mp4")


def test_upload_file_s3_success(storage, monkeypatch):
    """When S3 succeeds, upload_file uses transfer config and returns object key."""
    mock_s3 = MagicMock()
    monkeypatch.setattr(storage, "_get_client", lambda: mock_s3)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
        f.write(b"sample bytes")
        temp_file = f.name

    try:
        key = storage.upload_file(temp_file, "downloads/u/2026/11/j1.mp4", content_type="video/mp4")
        assert key == "downloads/u/2026/11/j1.mp4"
        mock_s3.upload_file.assert_called_once()
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def test_upload_and_local_fallback(storage, monkeypatch):
    """When S3 is unreachable, upload_file saves to local fallback directory."""
    mock_s3 = MagicMock()
    mock_s3.upload_file.side_effect = EndpointConnectionError(endpoint_url="http://localhost:9000")
    mock_s3.head_object.side_effect = EndpointConnectionError(endpoint_url="http://localhost:9000")
    monkeypatch.setattr(storage, "_get_client", lambda: mock_s3)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as f:
        f.write(b"sample video bytes content")
        temp_file = f.name

    object_key = "test_user/2026/11/test_fallback.mp4"
    try:
        saved_key = storage.upload_file(temp_file, object_key, content_type="video/mp4")
        assert saved_key == object_key

        # Verify existence
        assert storage.file_exists(object_key) is True

        # Verify size
        size = storage.get_file_size(object_key)
        assert size == len(b"sample video bytes content")

        # Verify local path
        local_path = storage.get_local_file_path(object_key)
        assert local_path is not None
        assert os.path.isfile(local_path)

        # Verify deletion
        assert storage.delete_file(object_key) is True
        assert storage.file_exists(object_key) is False

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        storage.delete_file(object_key)


def test_generate_presigned_url_with_disposition(storage, monkeypatch):
    """generate_presigned_url passes ResponseContentDisposition and ResponseContentType."""
    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://s3.example.com/downloads/file.mp4?signed=1"
    monkeypatch.setattr(storage, "_get_client", lambda: mock_s3)

    url = storage.generate_presigned_url(
        object_key="downloads/u1/2026/11/j1.mp4",
        expiration=600,
        filename="custom_video_name.mp4",
        content_type="video/mp4",
    )
    assert url == "https://s3.example.com/downloads/file.mp4?signed=1"

    mock_s3.generate_presigned_url.assert_called_once_with(
        ClientMethod="get_object",
        Params={
            "Bucket": storage.bucket_name,
            "Key": "downloads/u1/2026/11/j1.mp4",
            "ResponseContentDisposition": 'attachment; filename="custom_video_name.mp4"',
            "ResponseContentType": "video/mp4",
        },
        ExpiresIn=600,
    )


def test_ensure_bucket_exists_creates_bucket(storage, monkeypatch):
    """ensure_bucket_exists creates bucket with private ACL if it does not exist."""
    mock_s3 = MagicMock()
    error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
    mock_s3.head_bucket.side_effect = ClientError(error_response, "head_bucket")
    monkeypatch.setattr(storage, "_get_client", lambda: mock_s3)

    success = storage.ensure_bucket_exists()
    assert success is True
    mock_s3.create_bucket.assert_called_once()
    mock_s3.put_bucket_acl.assert_called_once_with(
        Bucket=storage.bucket_name,
        ACL="private",
    )


def test_local_path_traversal_prevention(storage):
    """get_local_file_path must reject directory traversal attempts."""
    traversal_key = "../../../../../etc/passwd"
    assert storage.get_local_file_path(traversal_key) is None

    windows_traversal = "..\\..\\..\\windows\\system32\\calc.exe"
    assert storage.get_local_file_path(windows_traversal) is None


def test_transfer_config_multipart_threshold():
    """Verify DEFAULT_TRANSFER_CONFIG has 50MB multipart threshold."""
    assert DEFAULT_TRANSFER_CONFIG.multipart_threshold == 50 * 1024 * 1024
    assert DEFAULT_TRANSFER_CONFIG.multipart_chunksize == 10 * 1024 * 1024
    assert DEFAULT_TRANSFER_CONFIG.use_threads is True
