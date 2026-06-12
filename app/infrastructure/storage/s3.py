import json
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
import structlog

from app.infrastructure.storage.base import StorageProvider

logger = structlog.get_logger()


class S3StorageProvider(StorageProvider):
    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        region_name: str = "us-east-1",
    ):
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.region_name = region_name

        session_args = {}
        if access_key and secret_key:
            session_args["aws_access_key_id"] = access_key
            session_args["aws_secret_access_key"] = secret_key
        if region_name:
            session_args["region_name"] = region_name

        # For MinIO compatibility, set signature_version to s3v4
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            config=Config(signature_version="s3v4"),
            **session_args
        )

        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
            logger.info("Bucket exists", bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchBucket"):
                logger.info("Creating bucket", bucket=self.bucket_name)
                # CreateBucket config differs if a region is specified and it's not us-east-1
                if self.region_name == "us-east-1" or self.endpoint_url:
                    self.client.create_bucket(Bucket=self.bucket_name)
                else:
                    self.client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={"LocationConstraint": self.region_name},
                    )

                # Set read-only policy for anonymous access on MinIO
                # This makes links directly downloadable without pre-signing
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "PublicRead",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"],
                        }
                    ],
                }
                self.client.put_bucket_policy(
                    Bucket=self.bucket_name, Policy=json.dumps(policy)
                )
            else:
                logger.error("Failed to check bucket existence", error=str(e))
                raise e

    def upload_file(self, local_path: str, object_name: str) -> str:
        # Determine content type (default to video/mp4)
        content_type = "video/mp4"
        if object_name.endswith(".png"):
            content_type = "image/png"

        try:
            self.client.upload_file(
                local_path,
                self.bucket_name,
                object_name,
                ExtraArgs={"ContentType": content_type},
            )
            logger.info("Uploaded file to S3/MinIO", bucket=self.bucket_name, object=object_name)
            return self.get_url(object_name)
        except Exception as e:
            logger.error("Failed to upload file to S3", object=object_name, error=str(e))
            raise e

    def download_file(self, object_name: str, dest_path: str) -> None:
        try:
            self.client.download_file(self.bucket_name, object_name, dest_path)
            logger.info("Downloaded file from S3/MinIO", bucket=self.bucket_name, object=object_name)
        except Exception as e:
            logger.error("Failed to download file from S3", object=object_name, error=str(e))
            raise e

    def delete_file(self, object_name: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_name)
            logger.info("Deleted file from S3/MinIO", bucket=self.bucket_name, object=object_name)
        except Exception as e:
            logger.error("Failed to delete file from S3", object=object_name, error=str(e))
            raise e

    def get_url(self, object_name: str) -> str:
        # If it's a local MinIO endpoint, return a direct public URL
        # because we provisioned a PublicRead bucket policy. This bypasses
        # signature host mismatch errors when accessed from localhost.
        if self.endpoint_url and "minio" in self.endpoint_url:
            return f"http://localhost:9000/{self.bucket_name}/{object_name}"

        try:
            url = self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": object_name},
                ExpiresIn=604800,  # 7 days
            )
            return url
        except Exception as e:
            logger.error("Failed to generate URL", object=object_name, error=str(e))
            raise e
