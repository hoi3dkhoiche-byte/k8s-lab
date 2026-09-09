import os
import uuid
import logging
from typing import Optional
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

logger = logging.getLogger("S3Client")

# ==============================================================================
# S3 CONFIGURATION (HỖ TRỢ CẢ NATIVE AWS S3, CLOUDFRONT LẪN S3-COMPATIBLE)
# ==============================================================================
AWS_REGION = os.environ.get("AWS_REGION", os.environ.get("S3_REGION", "ap-southeast-1"))
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "bida-caocap-images")
# S3_ENDPOINT_URL: Để trống nếu dùng AWS S3 chuẩn. Điền nếu dùng CMC / MinIO / LocalStack.
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "").strip() or None
# S3_PUBLIC_URL_PREFIX: Domain CloudFront CDN (ví dụ: https://d123456.cloudfront.net) hoặc custom domain
S3_PUBLIC_URL_PREFIX = os.environ.get("S3_PUBLIC_URL_PREFIX", "").rstrip("/")

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", os.environ.get("S3_ACCESS_KEY"))
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", os.environ.get("S3_SECRET_KEY"))

class S3StorageService:
    def __init__(self):
        self.bucket_name = S3_BUCKET_NAME
        self.region = AWS_REGION
        self.endpoint_url = S3_ENDPOINT_URL
        self.public_prefix = S3_PUBLIC_URL_PREFIX
        self.s3_client = None
        self._init_client()

    def _init_client(self):
        try:
            client_kwargs = {
                "region_name": self.region,
                "config": Config(signature_version="s3v4", s3={"addressing_style": "auto"})
            }
            
            # Nếu có endpoint tuỳ chỉnh (CMC Cloud, MinIO)
            if self.endpoint_url:
                client_kwargs["endpoint_url"] = self.endpoint_url
            
            # Nếu có truyền key cụ thể thì dùng, nếu không (trên AWS EKS) boto3 tự dùng IAM Role (IRSA)
            if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and not AWS_ACCESS_KEY_ID.startswith("cmc_access_key"):
                client_kwargs["aws_access_key_id"] = AWS_ACCESS_KEY_ID
                client_kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY

            self.s3_client = boto3.client("s3", **client_kwargs)
            logger.info(f"S3 Client initialized. Bucket: {self.bucket_name}, Region: {self.region}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")

    def upload_image(self, file_content: bytes, original_filename: str, content_type: str = "image/jpeg") -> str:
        """
        Uploads image to S3 bucket and returns public URL (via CloudFront CDN or direct S3 URL).
        """
        ext = original_filename.split('.')[-1].lower() if '.' in original_filename else 'jpg'
        file_key = f"products/{uuid.uuid4().hex}_{original_filename.replace(' ', '_')}"

        # Trường hợp dev chưa có S3: fallback an toàn
        if not self.s3_client:
            logger.warning("S3 Client not ready. Returning placeholder URL.")
            if self.public_prefix:
                return f"{self.public_prefix}/{file_key}"
            return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_key}"

        try:
            put_kwargs = {
                "Bucket": self.bucket_name,
                "Key": file_key,
                "Body": file_content,
                "ContentType": content_type
            }
            # Nếu không dùng Bucket Owner Enforced (ACLs disabled), có thể gửi public-read
            # Trên AWS S3 hiện đại khuyến nghị Object Ownership: Bucket Owner Enforced (dùng CloudFront hoặc Bucket Policy)
            try:
                put_kwargs["ACL"] = "public-read"
                self.s3_client.put_object(**put_kwargs)
            except ClientError as acl_err:
                # Fallback nếu bucket cấm ACL
                put_kwargs.pop("ACL", None)
                self.s3_client.put_object(**put_kwargs)

            # 1. Nếu có cấu hình CloudFront CDN
            if self.public_prefix:
                return f"{self.public_prefix}/{file_key}"

            # 2. Nếu là AWS S3 chuẩn
            if not self.endpoint_url or "amazonaws.com" in self.endpoint_url:
                return f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{file_key}"

            # 3. Nếu là S3-compatible bên thứ 3
            return f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{file_key}"

        except ClientError as e:
            logger.error(f"S3 Upload ClientError: {e}")
            raise RuntimeError(f"Lỗi tải ảnh lên S3: {str(e)}")
        except Exception as e:
            logger.error(f"S3 Upload Unexpected Error: {e}")
            raise RuntimeError(f"Không thể tải ảnh lên S3: {str(e)}")

s3_storage = S3StorageService()
