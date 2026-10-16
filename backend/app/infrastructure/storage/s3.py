"""Neon Object Storage adapter (S3-compatible) built on boto3.

Per Neon's docs: path-style addressing and SigV4 only, with the branch endpoint supplied via
AWS_ENDPOINT_URL_S3. Credentials are branch-scoped and passed explicitly from settings.
"""

import logging
import time
from urllib.parse import quote

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from mypy_boto3_s3 import S3Client

from app.domain.entities.health import ComponentHealth, ComponentState
from app.domain.entities.media import StoredObject
from app.domain.errors import NotFoundError, StorageUnavailableError

logger = logging.getLogger(__name__)

_NOT_FOUND_CODES = {"404", "NoSuchKey", "NotFound"}


def build_s3_client(
    *, endpoint_url: str, access_key_id: str, secret_access_key: str, region: str | None
) -> S3Client:
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region or "us-east-2",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            retries={"mode": "standard", "max_attempts": 4},  # handles SlowDown/503 backoff
            connect_timeout=5,
            read_timeout=30,
        ),
    )


def _error_code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))


class S3ObjectStorage:
    def __init__(
        self, client: S3Client, *, endpoint_url: str, public_base_url: str | None = None
    ) -> None:
        self._client = client
        self._public_base = (public_base_url or endpoint_url).rstrip("/")

    def put(
        self, bucket: str, key: str, data: bytes, *, content_type: str, cache_control: str
    ) -> None:
        try:
            self._client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                CacheControl=cache_control,
            )
        except (ClientError, BotoCoreError) as exc:
            logger.warning("Storage put failed for %s/%s: %s", bucket, key, type(exc).__name__)
            raise StorageUnavailableError("Could not store the file.") from exc

    def get(self, bucket: str, key: str) -> StoredObject:
        try:
            response = self._client.get_object(Bucket=bucket, Key=key)
            return StoredObject(
                data=response["Body"].read(), content_type=response.get("ContentType")
            )
        except ClientError as exc:
            if _error_code(exc) in _NOT_FOUND_CODES:
                raise NotFoundError("Object not found.") from exc
            raise StorageUnavailableError("Could not read the file.") from exc
        except BotoCoreError as exc:
            raise StorageUnavailableError("Could not read the file.") from exc

    def exists(self, bucket: str, key: str) -> bool:
        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as exc:
            if _error_code(exc) in _NOT_FOUND_CODES:
                return False
            raise StorageUnavailableError("Could not check the file.") from exc
        except BotoCoreError as exc:
            raise StorageUnavailableError("Could not check the file.") from exc

    def delete(self, bucket: str, key: str) -> None:
        try:
            self._client.delete_object(Bucket=bucket, Key=key)
        except (ClientError, BotoCoreError) as exc:
            raise StorageUnavailableError("Could not delete the file.") from exc

    def public_url(self, bucket: str, key: str) -> str:
        return f"{self._public_base}/{quote(bucket)}/{quote(key)}"

    def presigned_url(self, bucket: str, key: str, *, expires_in: int) -> str:
        try:
            return self._client.generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires_in
            )
        except (ClientError, BotoCoreError) as exc:
            raise StorageUnavailableError("Could not sign the URL.") from exc


class S3BucketHealthProbe:
    """HealthProbe: HeadBucket against the media bucket."""

    def __init__(self, client: S3Client, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    def check(self) -> ComponentHealth:
        started = time.perf_counter()
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except (ClientError, BotoCoreError) as exc:
            logger.warning("Storage health check failed: %s", type(exc).__name__)
            return ComponentHealth("storage", ComponentState.DOWN, detail="unreachable")
        latency = round((time.perf_counter() - started) * 1000, 2)
        return ComponentHealth(
            "storage", ComponentState.OK, latency_ms=latency, detail="neon-object-storage"
        )
