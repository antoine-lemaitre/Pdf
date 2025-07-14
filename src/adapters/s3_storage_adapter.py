try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    boto3 = None

from typing import Optional
from src.ports.file_storage_port import FileStoragePort
from src.domain.exceptions import FileStorageError


class S3StorageAdapter(FileStoragePort):
    """Adapter for Amazon S3 file storage."""
    
    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1"
    ):
        """
        Initialize the S3 adapter.
        
        Args:
            bucket_name: S3 bucket name
            aws_access_key_id: AWS access key (optional if configured via env/IAM)
            aws_secret_access_key: AWS secret key (optional if configured via env/IAM)
            region_name: AWS region
        """
        if boto3 is None:
            raise ImportError("boto3 is required for S3 storage. Install with: pip install boto3")
        
        self.bucket_name = bucket_name
        
        # Initialize S3 client
        session_kwargs = {"region_name": region_name}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs.update({
                "aws_access_key_id": aws_access_key_id,
                "aws_secret_access_key": aws_secret_access_key
            })
        
        try:
            session = boto3.Session(**session_kwargs)
            self.s3_client = session.client('s3')
            
            # Check that the bucket exists
            self.s3_client.head_bucket(Bucket=bucket_name)
            
        except NoCredentialsError:
            raise FileStorageError("AWS credentials not found")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise FileStorageError(f"Bucket {bucket_name} not found")
            else:
                raise FileStorageError(f"Error accessing S3: {str(e)}")
    
    def read_file(self, file_path: str) -> bytes:
        """
        Read a file from S3.
        
        Args:
            file_path: S3 key of the file
            
        Returns:
            bytes: File content
            
        Raises:
            FileStorageError: In case of read error
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_path)
            return response['Body'].read()
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise FileStorageError(f"File {file_path} not found in S3")
            else:
                raise FileStorageError(f"Error reading file from S3: {str(e)}")
        except Exception as e:
            raise FileStorageError(f"Unexpected error reading file from S3: {str(e)}")
    
    def write_file(self, file_path: str, content: bytes) -> None:
        """
        Write a file to S3.
        
        Args:
            file_path: S3 destination key
            content: Content to write
            
        Raises:
            FileStorageError: In case of write error
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=file_path,
                Body=content
            )
            
        except ClientError as e:
            raise FileStorageError(f"Error writing file to S3: {str(e)}")
        except Exception as e:
            raise FileStorageError(f"Unexpected error writing file to S3: {str(e)}")
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in S3.
        
        Args:
            file_path: S3 key of the file
            
        Returns:
            bool: True if the file exists
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_path)
            return True
        except ClientError:
            return False
        except Exception:
            return False
    
    def delete_file(self, file_path: str) -> None:
        """
        Delete a file from S3.
        
        Args:
            file_path: S3 key of the file to delete
            
        Raises:
            FileStorageError: In case of deletion error
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_path)
            
        except ClientError as e:
            raise FileStorageError(f"Error deleting file from S3: {str(e)}")
        except Exception as e:
            raise FileStorageError(f"Unexpected error deleting file from S3: {str(e)}") 