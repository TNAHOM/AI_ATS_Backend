import io
import uuid
import logging
import asyncio
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from app.core.config import settings
from app.core.exceptions import S3ServiceError

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            self.bucket_name = settings.S3_BUCKET_NAME
        except (ClientError, BotoCoreError, TypeError, ValueError) as e:
            logger.error(f"Failed to initialize Boto3 client: {e}")
            raise S3ServiceError("Storage service initialization failed.") from e

    async def upload_document(self, file_bytes: bytes, original_filename: str, content_type: str = "application/pdf") -> str:
        """
        Uploads a file to S3 in a non-blocking way.
        Returns the unique S3 object key (not the full URL).
        """
        # Generate a unique safe filename to prevent overwrites
        extension = original_filename.split('.')[-1] if '.' in original_filename else 'pdf'
        unique_key = f"{uuid.uuid4().hex}.{extension}"
        
        # Convert bytes to a file-like object
        file_obj = io.BytesIO(file_bytes)

        try:
            await asyncio.to_thread(
                self.s3_client.upload_fileobj,
                Fileobj=file_obj,
                Bucket=self.bucket_name,
                Key=unique_key,
                ExtraArgs={
                    "ContentType": content_type, # CRITICAL: Tells browser to render, not download
                    "ContentDisposition": "inline" 
                }
            )
            logger.info(f"Successfully uploaded {original_filename} as {unique_key} to S3.")
            return unique_key

        except (ClientError, BotoCoreError) as e:
            logger.error(f"AWS S3 Upload Error: {str(e)}")
            raise S3ServiceError("Failed to upload document to storage.")
        except (TypeError, ValueError, OSError, RuntimeError) as e:
            logger.exception(f"Unexpected error during S3 upload: {str(e)}")
            raise S3ServiceError("An internal error occurred during upload.") from e

    async def download_document(self, s3_key: str) -> bytes:
        """
        Downloads a file from S3 by its object key and returns the raw bytes.
        """
        output_buffer = io.BytesIO()
        try:
            await asyncio.to_thread(
                self.s3_client.download_fileobj,
                Bucket=self.bucket_name,
                Key=s3_key,
                Fileobj=output_buffer,
            )
            return output_buffer.getvalue()
        except (ClientError, BotoCoreError) as e:
            logger.error(f"AWS S3 Download Error for key '{s3_key}': {str(e)}")
            raise S3ServiceError("Failed to download document from storage.")
        except (TypeError, ValueError, OSError, RuntimeError) as e:
            logger.exception(f"Unexpected error during S3 download for key '{s3_key}': {str(e)}")
            raise S3ServiceError("An internal error occurred during download.") from e

    async def delete_document(self, s3_key: str) -> None:
        """
        Deletes an object from S3 by its key. Used for best-effort cleanup on
        upload rollbacks (e.g. when a database commit fails after a successful
        S3 upload).
        """
        try:
            await asyncio.to_thread(
                self.s3_client.delete_object,
                Bucket=self.bucket_name,
                Key=s3_key,
            )
            logger.info(f"Successfully deleted S3 object '{s3_key}'.")
        except (ClientError, BotoCoreError) as e:
            logger.error(f"AWS S3 Delete Error for key '{s3_key}': {str(e)}")
            raise S3ServiceError("Failed to delete document from storage.")
        except (TypeError, ValueError, OSError, RuntimeError) as e:
            logger.exception(f"Unexpected error during S3 delete for key '{s3_key}': {str(e)}")
            raise S3ServiceError("An internal error occurred during delete.") from e


s3_service = S3Service()