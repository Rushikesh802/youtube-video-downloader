"""
Object storage service supporting AWS S3 and MinIO with local filesystem fallback.

Handles:
  - Deterministic object key generation
  - Multi-part uploads for large media assets (>50MB) via TransferConfig
  - Bucket existence and private access policy enforcement
  - Short-lived presigned GET URLs with custom Content-Disposition filename headers
  - File existence, size lookup, and deletion across S3 and fallback storage
"""
from datetime import datetime, timezone
import json
import logging
import os
import shutil
from typing import Optional

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.client import Config
from botocore.exceptions import ClientError, EndpointConnectionError

from app.config import settings

logger = logging.getLogger("yt_downloader.storage")

# Multipart transfer configuration: files > 50MB split into 10MB parts
MB = 1024 * 1024
DEFAULT_TRANSFER_CONFIG = TransferConfig(
    multipart_threshold=50 * MB,
    max_concurrency=10,
    multipart_chunksize=10 * MB,
    use_threads=True,
)


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
                config=Config(
                    signature_version="s3v4",
                    s3={"addressing_style": "path"},
                    connect_timeout=2,
                    read_timeout=2,
                    retries={"max_attempts": 1},
                ),
            )
        return self._s3_client

    @staticmethod
    def generate_object_key(
        user_id: str,
        job_id: str,
        format_str: str,
        timestamp: Optional[datetime] = None,
    ) -> str:
        """
        Generate deterministic and collision-free object key.
        Pattern: downloads/{user_id}/{year}/{month:02d}/{job_id}.{format}
        """
        dt = timestamp or datetime.now(timezone.utc)
        clean_ext = format_str.lstrip(".")
        return f"downloads/{user_id}/{dt.year}/{dt.month:02d}/{job_id}.{clean_ext}"

    def ensure_bucket_exists(self) -> bool:
        """
        Verifies that the target bucket exists and enforces a private access policy.
        If the bucket does not exist (e.g. in fresh local MinIO), attempts to create it
        and apply a private ACL to disallow public read access.
        """
        try:
            client = self._get_client()
            try:
                client.head_bucket(Bucket=self.bucket_name)
            except ClientError as exc:
                error_code = str(exc.response.get("Error", {}).get("Code", ""))
                if error_code in ("404", "NoSuchBucket"):
                    logger.info("Bucket %s does not exist, creating bucket...", self.bucket_name)
                    create_params = {"Bucket": self.bucket_name}
                    if self.region and self.region != "us-east-1":
                        create_params["CreateBucketConfiguration"] = {
                            "LocationConstraint": self.region
                        }
                    client.create_bucket(**create_params)
                else:
                    raise exc

            # Enforce private ACL
            try:
                client.put_bucket_acl(Bucket=self.bucket_name, ACL="private")
            except Exception as acl_exc:
                logger.debug("Could not set private ACL on bucket %s: %s", self.bucket_name, acl_exc)

            return True
        except (ClientError, EndpointConnectionError, Exception) as exc:
            logger.warning("ensure_bucket_exists could not reach S3/MinIO (%s). Local fallback remains active.", exc)
            return False

    def upload_file(
        self,
        local_path: str,
        object_key: str,
        content_type: Optional[str] = None,
        transfer_config: Optional[TransferConfig] = None,
    ) -> str:
        """
        Upload local file to S3/MinIO using multipart transfer for large files.
        Falls back to local filesystem store if S3 service is not reachable.
        """
        if not os.path.isfile(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        cfg = transfer_config or DEFAULT_TRANSFER_CONFIG

        try:
            client = self._get_client()
            client.upload_file(
                Filename=local_path,
                Bucket=self.bucket_name,
                Key=object_key,
                ExtraArgs=extra_args if extra_args else None,
                Config=cfg,
            )
            logger.info("Uploaded %s to s3://%s/%s (multipart enabled)", local_path, self.bucket_name, object_key)
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
            shutil.copy2(local_path, target_path)
            return object_key

    def generate_presigned_url(
        self,
        object_key: str,
        expiration: Optional[int] = None,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> str:
        """
        Generate a short-lived presigned GET URL for secure downloading.
        Optionally attaches Content-Disposition header to trigger browser save dialog
        with a sanitized, human-readable filename.
        """
        expires = expiration or self.presigned_expiry
        params = {"Bucket": self.bucket_name, "Key": object_key}

        if filename:
            # Force browser download prompt with the specified filename
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
        if content_type:
            params["ResponseContentType"] = content_type

        try:
            client = self._get_client()
            url = client.generate_presigned_url(
                ClientMethod="get_object",
                Params=params,
                ExpiresIn=expires,
            )
            return url
        except Exception as exc:
            logger.warning("Failed to generate presigned S3 URL (%s). Using fallback URL.", exc)
            # Fallback URL for local storage serving
            return f"/api/v1/downloads/files/{object_key}"

    def delete_file(self, object_key: str) -> bool:
        """Delete object from both S3 and local fallback storage."""
        deleted = False

        # Try deleting from S3
        try:
            client = self._get_client()
            client.delete_object(Bucket=self.bucket_name, Key=object_key)
            deleted = True
            logger.info("Deleted s3://%s/%s", self.bucket_name, object_key)
        except Exception as exc:
            logger.debug("S3 delete failed or skipped: %s", exc)

        # Also clean from local fallback if present
        local_target = os.path.join(self.local_storage_dir, object_key.replace("/", os.sep))
        if os.path.exists(local_target):
            try:
                os.remove(local_target)
                deleted = True
                logger.info("Deleted local fallback file: %s", local_target)
            except OSError:
                pass

        return deleted

    def file_exists(self, object_key: str) -> bool:
        """Check if an object exists in either S3 or local storage."""
        try:
            client = self._get_client()
            client.head_object(Bucket=self.bucket_name, Key=object_key)
            return True
        except ClientError:
            local_target = os.path.join(self.local_storage_dir, object_key.replace("/", os.sep))
            return os.path.isfile(local_target)
        except Exception:
            local_target = os.path.join(self.local_storage_dir, object_key.replace("/", os.sep))
            return os.path.isfile(local_target)

    def get_file_size(self, object_key: str) -> Optional[int]:
        """Retrieve file size in bytes from S3 or local fallback."""
        try:
            client = self._get_client()
            resp = client.head_object(Bucket=self.bucket_name, Key=object_key)
            return resp.get("ContentLength")
        except Exception:
            local_target = os.path.join(self.local_storage_dir, object_key.replace("/", os.sep))
            if os.path.isfile(local_target):
                return os.path.getsize(local_target)
            return None

    def get_local_file_path(self, object_key: str) -> Optional[str]:
        """Return absolute path if file exists in local storage fallback."""
        local_target = os.path.abspath(
            os.path.join(self.local_storage_dir, object_key.replace("/", os.sep))
        )
        # Ensure path traversal protection: target must be inside local_storage_dir
        if not local_target.startswith(self.local_storage_dir):
            return None
        if os.path.isfile(local_target):
            return local_target
        return None


storage_service = StorageService()
