"""
Factory for creating PDF processors.
Implements the PdfProcessorFactoryPort to create concrete PDF processors.
"""
from typing import Dict, Any
from ..ports.pdf_processor_factory_port import PdfProcessorFactoryPort
from ..ports.pdf_processor_port import PdfProcessorPort
from ..ports.file_storage_port import FileStoragePort
from .pymupdf_adapter import PyMuPdfAdapter
from .pypdfium2_adapter import PyPdfium2Adapter
from .pdfplumber_adapter import PdfPlumberAdapter
from ..domain.exceptions import ObfuscationError


class PdfProcessorFactory(PdfProcessorFactoryPort):
    """Factory for creating PDF processors."""
    
    def __init__(self):
        """Initialize the factory with supported engines."""
        self._supported_engines = {
            "pymupdf": {
                "name": "PyMuPDF",
                "version": "1.26.3+",
                "description": "Fast PDF processing with PyMuPDF",
                "capabilities": ["text_extraction", "obfuscation", "flattening"]
            },
            "pypdfium2": {
                "name": "PyPDFium2",
                "version": "4.30.0+",
                "description": "Google PDFium-based processing",
                "capabilities": ["text_extraction", "obfuscation", "flattening"]
            },
            "pdfplumber": {
                "name": "pdfplumber",
                "version": "0.10.0+",
                "description": "Text extraction focused processing",
                "capabilities": ["text_extraction", "obfuscation"]
            }
        }
    
    def create_processor(self, engine: str, file_storage: FileStoragePort) -> PdfProcessorPort:
        """
        Create a PDF processor for the specified engine.
        
        Args:
            engine: Engine name (pymupdf, pypdfium2, pdfplumber)
            file_storage: File storage system to use
            
        Returns:
            Configured PDF processor
            
        Raises:
            ObfuscationError: If engine is not supported
        """
        if engine not in self._supported_engines:
            supported = ", ".join(self._supported_engines.keys())
            raise ObfuscationError(f"Engine '{engine}' not supported. Available engines: {supported}")
        
        try:
            if engine == "pymupdf":
                return PyMuPdfAdapter(file_storage)
            elif engine == "pypdfium2":
                return PyPdfium2Adapter(file_storage)
            elif engine == "pdfplumber":
                return PdfPlumberAdapter(file_storage)
            else:
                raise ObfuscationError(f"Unknown engine: {engine}")
        except Exception as e:
            raise ObfuscationError(f"Failed to create processor for engine '{engine}': {str(e)}")
    
    def get_supported_engines(self) -> list[str]:
        """Get list of supported engine names."""
        return list(self._supported_engines.keys())
    
    def get_engine_info(self, engine: str) -> Dict[str, Any]:
        """
        Get information about a specific engine.
        
        Args:
            engine: Engine name
            
        Returns:
            Engine information dictionary
            
        Raises:
            ObfuscationError: If engine is not supported
        """
        if engine not in self._supported_engines:
            supported = ", ".join(self._supported_engines.keys())
            raise ObfuscationError(f"Engine '{engine}' not supported. Available engines: {supported}")
        
        return self._supported_engines[engine].copy()
