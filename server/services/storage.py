import boto3
from botocore.config import Config
from config import get_settings
import os

settings = get_settings()


def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
    )


async def upload_to_r2(file_content: bytes, key: str) -> str:
    """Upload file to R2 and return the object key"""
    client = get_r2_client()
    client.put_object(
        Bucket=settings.r2_bucket_name,
        Key=key,
        Body=file_content
    )
    return key


async def download_from_r2(key: str, local_path: str) -> str:
    """Download file from R2 to local path"""
    client = get_r2_client()
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    client.download_file(settings.r2_bucket_name, key, local_path)
    return local_path


async def delete_from_r2(key: str):
    """Delete file from R2"""
    client = get_r2_client()
    client.delete_object(Bucket=settings.r2_bucket_name, Key=key)
