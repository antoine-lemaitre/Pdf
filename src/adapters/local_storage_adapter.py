import os
from pathlib import Path
from src.ports.file_storage_port import FileStoragePort
from src.domain.exceptions import FileStorageError


class LocalStorageAdapter(FileStoragePort):
    """Adapter for local file storage."""
    
    def __init__(self, base_path: str = "."):
        """
        Initialize the local storage adapter.
        
        Args:
            base_path: Base directory for file operations
        """
        self.base_path = Path(base_path).resolve()
    
    def read_file(self, file_path: str) -> bytes:
        """
        Read a file from the local file system.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bytes: File content
            
        Raises:
            FileStorageError: In case of read error
        """
        try:
            resolved_path = self._resolve_path(file_path)
            
            if not resolved_path.exists():
                raise FileStorageError(f"File {resolved_path} does not exist")
            
            if not resolved_path.is_file():
                raise FileStorageError(f"{resolved_path} is not a file")
            
            with open(resolved_path, 'rb') as f:
                return f.read()
                
        except FileStorageError:
            raise
        except Exception as e:
            raise FileStorageError(f"Error reading file {file_path}: {str(e)}")
    
    def write_file(self, file_path: str, content: bytes) -> None:
        """
        Write a file to the local file system.
        
        Args:
            file_path: Destination path
            content: Content to write
            
        Raises:
            FileStorageError: In case of write error
        """
        try:
            resolved_path = self._resolve_path(file_path)
            
            # Create parent directories if necessary
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(resolved_path, 'wb') as f:
                f.write(content)
                
        except Exception as e:
            raise FileStorageError(f"Error writing file {file_path}: {str(e)}")
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if the file exists
        """
        try:
            resolved_path = self._resolve_path(file_path)
            return resolved_path.exists() and resolved_path.is_file()
        except Exception:
            return False
    
    def delete_file(self, file_path: str) -> None:
        """
        Delete a file.
        
        Args:
            file_path: Path to the file to delete
            
        Raises:
            FileStorageError: In case of deletion error
        """
        try:
            resolved_path = self._resolve_path(file_path)
            
            if resolved_path.exists():
                resolved_path.unlink()
                
        except Exception as e:
            raise FileStorageError(f"Error deleting file {file_path}: {str(e)}")
    
    def _resolve_path(self, file_path: str) -> Path:
        """
        Resolve a relative path with respect to the base directory.
        
        Args:
            file_path: File path
            
        Returns:
            Path: Resolved path
        """
        path = Path(file_path)
        
        if path.is_absolute():
            return path
        else:
            return self.base_path / path 