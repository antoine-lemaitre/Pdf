"""
Port for PDF processor factory.
Defines the contract for creating PDF processors.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from .pdf_processor_port import PdfProcessorPort
from .file_storage_port import FileStoragePort


class PdfProcessorFactoryPort(ABC):
    """Port for creating PDF processors."""
    
    @abstractmethod
    def create_processor(self, engine: str, file_storage: FileStoragePort) -> PdfProcessorPort:
        """
        Create a PDF processor for the specified engine.
        
        Args:
            engine: Engine name (pymupdf, pypdfium2, pdfplumber)
            file_storage: File storage system to use
            
        Returns:
            Configured PDF processor
            
        Raises:
            ValueError: If engine is not supported
        """
        pass
    
    @abstractmethod
    def get_supported_engines(self) -> list[str]:
        """Get list of supported engine names."""
        pass
    
    @abstractmethod
    def get_engine_info(self, engine: str) -> Dict[str, Any]:
        """Get information about a specific engine."""
        pass
