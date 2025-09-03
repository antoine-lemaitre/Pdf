"""
Factory for creating PDF processors.
Implements the PdfProcessorFactoryPort to create concrete PDF processors.
"""
from typing import Dict, Any, Type
from ..ports.pdf_processor_factory_port import PdfProcessorFactoryPort
from ..ports.pdf_processor_port import PdfProcessorPort
from ..ports.file_storage_port import FileStoragePort
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
            # Dynamic import to avoid circular dependencies and respect architecture
            if engine == "pymupdf":
                from .pymupdf_adapter import PyMuPdfAdapter
                return PyMuPdfAdapter(file_storage)
            elif engine == "pypdfium2":
                from .pypdfium2_adapter import PyPdfium2Adapter
                return PyPdfium2Adapter(file_storage)
            elif engine == "pdfplumber":
                from .pdfplumber_adapter import PdfPlumberAdapter
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
    
    def register_engine(self, engine_name: str, engine_info: Dict[str, Any]) -> None:
        """
        Register a new engine with the factory.
        
        Args:
            engine_name: Name of the engine to register
            engine_info: Engine information dictionary
        """
        self._supported_engines[engine_name] = engine_info.copy()
    
    def unregister_engine(self, engine_name: str) -> bool:
        """
        Unregister an engine from the factory.
        
        Args:
            engine_name: Name of the engine to unregister
            
        Returns:
            True if engine was unregistered, False if it wasn't found
        """
        if engine_name in self._supported_engines:
            del self._supported_engines[engine_name]
            return True
        return False
