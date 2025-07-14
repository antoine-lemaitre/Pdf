try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    boto3 = None

from typing import Optional
from src.ports.file_storage_port import FileStoragePort
from src.domain.exceptions import FileStorageError


class S3StorageAdapter(FileStoragePort):
    """Adapter pour le stockage de fichiers sur Amazon S3."""
    
    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1"
    ):
        """
        Initialise l'adapter S3.
        
        Args:
            bucket_name: Nom du bucket S3
            aws_access_key_id: Clé d'accès AWS (optionnel si configuré via env/IAM)
            aws_secret_access_key: Clé secrète AWS (optionnel si configuré via env/IAM)
            region_name: Région AWS
        """
        if boto3 is None:
            raise ImportError("boto3 is required for S3 storage. Install with: pip install boto3")
        
        self.bucket_name = bucket_name
        
        # Initialiser le client S3
        session_kwargs = {"region_name": region_name}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs.update({
                "aws_access_key_id": aws_access_key_id,
                "aws_secret_access_key": aws_secret_access_key
            })
        
        try:
            session = boto3.Session(**session_kwargs)
            self.s3_client = session.client('s3')
            
            # Vérifier que le bucket existe
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
        Lit un fichier depuis S3.
        
        Args:
            file_path: Clé S3 du fichier
            
        Returns:
            bytes: Contenu du fichier
            
        Raises:
            FileStorageError: En cas d'erreur de lecture
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
        Écrit un fichier vers S3.
        
        Args:
            file_path: Clé S3 de destination
            content: Contenu à écrire
            
        Raises:
            FileStorageError: En cas d'erreur d'écriture
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
        Vérifie si un fichier existe dans S3.
        
        Args:
            file_path: Clé S3 du fichier
            
        Returns:
            bool: True si le fichier existe
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
        Supprime un fichier de S3.
        
        Args:
            file_path: Clé S3 du fichier à supprimer
            
        Raises:
            FileStorageError: En cas d'erreur de suppression
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=file_path)
            
        except ClientError as e:
            raise FileStorageError(f"Error deleting file from S3: {str(e)}")
        except Exception as e:
            raise FileStorageError(f"Unexpected error deleting file from S3: {str(e)}") 