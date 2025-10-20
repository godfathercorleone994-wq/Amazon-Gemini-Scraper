"""
AWS S3 storage for files and backups
"""
from typing import Optional, BinaryIO, List
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import io

from config.settings import settings
from utils.logger import logger

class S3Storage:
    """AWS S3 storage manager"""
    
    def __init__(self):
        self.s3_client = None
        self.bucket_name = settings.s3_bucket_name
        self._initialized = False
    
    def connect(self):
        """Initialize S3 client"""
        if self._initialized:
            return
        
        try:
            if not settings.aws_access_key_id or not settings.aws_secret_access_key:
                logger.warning("AWS credentials not configured, S3 storage disabled")
                return
            
            logger.info("Initializing S3 client...")
            
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region
            )
            
            # Verify bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            
            self._initialized = True
            logger.info(f"S3 client initialized for bucket: {self.bucket_name}")
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
        except ClientError as e:
            logger.error(f"S3 client initialization error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected S3 error: {str(e)}")
    
    def upload_file(
        self,
        file_data: BinaryIO,
        key: str,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """Upload file to S3"""
        try:
            if not self._initialized:
                self.connect()
            
            if not self._initialized:
                return False
            
            extra_args = {}
            
            if content_type:
                extra_args['ContentType'] = content_type
            
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_fileobj(
                file_data,
                self.bucket_name,
                key,
                ExtraArgs=extra_args if extra_args else None
            )
            
            logger.info(f"File uploaded to S3: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 upload error: {str(e)}")
            return False
    
    def download_file(self, key: str) -> Optional[bytes]:
        """Download file from S3"""
        try:
            if not self._initialized:
                self.connect()
            
            if not self._initialized:
                return None
            
            buffer = io.BytesIO()
            self.s3_client.download_fileobj(self.bucket_name, key, buffer)
            
            logger.info(f"File downloaded from S3: {key}")
            return buffer.getvalue()
            
        except ClientError as e:
            logger.error(f"S3 download error: {str(e)}")
            return None
    
    def delete_file(self, key: str) -> bool:
        """Delete file from S3"""
        try:
            if not self._initialized:
                self.connect()
            
            if not self._initialized:
                return False
            
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            
            logger.info(f"File deleted from S3: {key}")
            return True
            
        except ClientError as e:
            logger.error(f"S3 delete error: {str(e)}")
            return False
    
    def generate_presigned_url(self, key: str, expiration: int = 3600) -> Optional[str]:
        """Generate presigned URL for temporary access"""
        try:
            if not self._initialized:
                self.connect()
            
            if not self._initialized:
                return None
            
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': key},
                ExpiresIn=expiration
            )
            
            return url
            
        except ClientError as e:
            logger.error(f"S3 presigned URL error: {str(e)}")
            return None
    
    def list_files(self, prefix: str = "") -> List[str]:
        """List files in S3 bucket"""
        try:
            if not self._initialized:
                self.connect()
            
            if not self._initialized:
                return []
            
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return []
            
            return [obj['Key'] for obj in response['Contents']]
            
        except ClientError as e:
            logger.error(f"S3 list error: {str(e)}")
            return []
    
    def save_screenshot(self, asin: str, screenshot_data: bytes) -> Optional[str]:
        """Save product screenshot to S3"""
        key = f"screenshots/{asin}/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.png"
        
        buffer = io.BytesIO(screenshot_data)
        success = self.upload_file(
            buffer,
            key,
            content_type="image/png",
            metadata={"asin": asin}
        )
        
        return key if success else None
    
    def save_html_snapshot(self, asin: str, html_content: str) -> Optional[str]:
        """Save HTML snapshot to S3"""
        key = f"html/{asin}/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.html"
        
        buffer = io.BytesIO(html_content.encode('utf-8'))
        success = self.upload_file(
            buffer,
            key,
            content_type="text/html",
            metadata={"asin": asin}
        )
        
        return key if success else None
    
    def backup_database(self, backup_data: bytes, backup_name: str) -> bool:
        """Backup database to S3"""
        key = f"backups/{backup_name}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        buffer = io.BytesIO(backup_data)
        return self.upload_file(
            buffer,
            key,
            content_type="application/json"
        )

# Global S3 storage instance
s3_storage = S3Storage()

def get_s3() -> S3Storage:
    """Get S3 storage instance"""
    if not s3_storage._initialized:
        s3_storage.connect()
    return s3_storage
