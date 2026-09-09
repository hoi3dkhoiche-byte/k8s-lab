import os
import uuid
import logging
from typing import Optional
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

logger = logging.getLogger("S3Client")

S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "https://s3.cloud.cmctelecom.vn")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "bida-caocap-images")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "cmc_access_key_placeholder")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "cmc_secret_key_placeholder")
S3_REGION = os.environ.get("S3_REGION", "ap-southeast-1")
S3_PUBLIC_URL_PREFIX = os.environ.get("S3_PUBLIC_URL_PREFIX", "")

class CMCCloudS3Storage:
    def __init__(self):
        self.endpoint_url = S3_ENDPOINT_URL
        self.bucket_name = S3_BUCKET_NAME
        self.access_key = S3_ACCESS_KEY
        self.secret_key = S3_SECRET_KEY
        self.public_prefix = S3_PUBLIC_URL_PREFIX.rstrip("/") if S3_PUBLIC_URL_PREFIX else None
        
        self.s3_client = None
        self._init_client()

    def _init_client(self):
        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self.endpoint_url,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=S3_REGION,
                config=Config(signature_version='s3v4', s3={'addressing_style': 'path'})
            )
            logger.info(f"Initialized S3 Client with endpoint: {self.endpoint_url}, bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")

    def upload_image(self, file_content: bytes, original_filename: str, content_type: str = "image/jpeg") -> str:
        """
        Uploads image to CMC S3 and returns the public URL.
        """
        ext = original_filename.split('.')[-1].lower() if '.' in original_filename else 'jpg'
        file_key = f"products/{uuid.uuid4().hex}_{original_filename.replace(' ', '_')}"

        # If dummy keys are used (e.g. local dev without CMC credentials yet), generate a safe fallback URL
        if not self.s3_client or self.access_key == "cmc_access_key_placeholder":
            logger.warning("S3 credentials not configured or placeholder used. Generating mock S3 URL.")
            if self.public_prefix:
                return f"{self.public_prefix}/{file_key}"
            return f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{file_key}"

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=file_content,
                ContentType=content_type,
                ACL='public-read'
            )
            
            if self.public_prefix:
                return f"{self.public_prefix}/{file_key}"
            return f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{file_key}"
        except ClientError as e:
            logger.error(f"S3 Upload error: {e}")
            raise RuntimeError(f"Không thể upload ảnh lên S3 CMC Cloud: {str(e)}")

s3_storage = CMCCloudS3Storage()
