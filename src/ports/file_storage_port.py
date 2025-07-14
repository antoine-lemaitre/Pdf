"""
Port for file storage operations.
This is an interface that defines how the domain can interact with file storage systems.
"""
from abc import ABC, abstractmethod
from typing import Optional

from ..domain.entities import Document


class FileStoragePort(ABC):
    """Interface for file storage operations."""
    
    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists at the given path.
        
        Args:
            file_path: The file path to check
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    def read_file(self, file_path: str) -> bytes:
        """
        Read file content as bytes.
        
        Args:
            file_path: The file path to read
            
        Returns:
            File content as bytes
            
        Raises:
            FileStorageError: If there's an error reading the file
        """
        pass
    
    @abstractmethod
    def write_file(self, file_path: str, content: bytes) -> None:
        """
        Write content to a file.
        
        Args:
            file_path: The file path to write to
            content: The content to write
            
        Raises:
            FileStorageError: If there's an error writing the file
        """
        pass
    
    @abstractmethod
    def delete_file(self, file_path: str) -> None:
        """
        Delete a file.
        
        Args:
            file_path: The file path to delete
            
        Raises:
            FileStorageError: If there's an error deleting the file
        """
        pass 