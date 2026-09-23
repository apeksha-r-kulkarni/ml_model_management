from minio import Minio
from minio.error import S3Error
import io

class MinioStorageService:
    """Service class for handling MinIO interactions."""
    
    def __init__(self, endpoint, access_key, secret_key, bucket_name, secure=False):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=secure,
            cert_check=False,
        )
        
        # Ensure bucket exists
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error:
            pass

    def upload_model(self, file_path: str, object_name: str) -> dict:
        """Uploads a model artifact to MinIO directly from file."""
        try:
            result = self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type="application/octet-stream",
            )
            return {
                "success": True,
                "object_name": result.object_name,
                "etag": result.etag,
                "path": f"s3://{self.bucket_name}/{result.object_name}"
            }
        except S3Error as e:
            return {
                "success": False,
                "error": str(e),
            }

    def delete_model(self, object_name: str) -> dict:
        """Deletes a model artifact from MinIO."""
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
            )
            return {"success": True}
        except S3Error as e:
            return {"success": False, "error": str(e)}
