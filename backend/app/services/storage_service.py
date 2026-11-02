"""
Object storage service supporting AWS S3 and MinIO with local filesystem fallback.

Handles file upload, deletion, existence checks, and generating short-lived
presigned GET URLs for secure file delivery.
"""
import os
import logging
from typing import Optional
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, EndpointConnectionError

from app.config import settings

logger = logging.getLogger("yt_downloader.storage")


class StorageService:
    """Manages object storage operations for downloaded media files."""

    def __init__(self):
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.S3_REGION
        self.presigned_expiry = settings.S3_PRESIGNED_EXPIRATION_SECONDS

        # Local storage fallback directory for offline development / testing
        self.local_storage_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "storage")
        )
        os.makedirs(self.local_storage_dir, exist_ok=True)

        self._s3_client = None

    def _get_client(self):
        if self._s3_client is None:
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url if self.endpoint_url else None,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            )
        return self._s3_client

    def upload_file(
        self,
        local_path: str,
        object_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """
        Upload local file to S3/MinIO. If S3 service is not reachable,
        falls back to local filesystem store for development/testing.
        """
        if not os.path.isfile(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        try:
            client = self._get_client()
            client.upload_file(
                Filename=local_path,
                Bucket=self.bucket_name,
                Key=object_key,
                ExtraArgs=extra_args if extra_args else None,
            )
            logger.info("Uploaded %s to s3://%s/%s", local_path, self.bucket_name, object_key)
            return object_key
        except (ClientError, EndpointConnectionError, Exception) as exc:
            logger.warning(
                "S3 upload failed (%s). Storing file locally in %s",
                exc,
                self.local_storage_dir,
            )
            # Local fallback storage
            target_path = os.path.join(self.local_storage_dir, object_key.replace("/", os.sep))
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            import shutil
            shutil.copy2(local_path, target_path)
            return object_key

    def generate_presigned_url(
        self,
        object_key: str,
        expiration: Optional[int] = None,
    ) -> str:
        """Generate a short-lived presigned GET URL for secure downloading."""
        expires = expiration or self.presigned_expiry
        try:
            client = self._get_client()
            url = client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": object_key},
                ExpiresIn=expires,
            )
            return url
        except Exception as exc:
            logger.warning("Failed to generate presigned S3 URL (%s). Using fallback URL.", exc)
            # Fallback URL for local storage
            return f"/api/v1/downloads/files/{object_key}"

    def delete_file(self, object_key: str) -> bool:
        """Delete object from storage."""
        # Try deleting from S3
        deleted = False
        try:
            client = self._get_client()
            client.delete_object(Bucket=self.bucket_name, Key=object_key)
            deleted = True
        except Exception as exc:
            logger.debug("S3 delete failed or skipped: %s", exc)

        # Also clean from local fallback if present
        local_target = os.path.join(self.local_storage_dir, object_key.replace("/", os.sep))
        if os.path.exists(local_target):
            try:
                os.remove(local_target)
                deleted = True
            except OSError:
                pass

        return deleted

    def file_exists(self, object_key: str) -> bool:
        """Check if an object exists in storage."""
        try:
            client = self._get_client()
            client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError:
            # Check local fallback
            local_target = os.path.join(self.local_storage_dir, object_key.replace("/", os.sep))
            return os.path.isfile(local_target)
        except Exception:
            local_target = os.path.join(self.local_storage_dir, object_key.replace("/", os.sep))
            return os.path.isfile(local_target)


storage_service = StorageService()
