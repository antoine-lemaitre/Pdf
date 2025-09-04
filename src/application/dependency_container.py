"""
Dependency container for PDF obfuscation application.
Centralizes the creation of all dependencies to maintain clean architecture.
"""
from typing import Optional
from ..ports.pdf_processor_port import PdfProcessorPort
from ..ports.file_storage_port import FileStoragePort
from ..ports.quality_evaluator_port import QualityEvaluatorPort
from ..ports.text_extractor_port import TextExtractorPort
from ..domain.services.configuration_service import ConfigurationService
from ..domain.services.document_obfuscation_service import DocumentObfuscationService
from ..domain.services.quality_evaluation_service import QualityEvaluationService
from ..domain.services.error_handler import ErrorHandler


class DependencyContainer:
    """Container for managing application dependencies."""
    
    def __init__(self):
        """Initialize the dependency container."""
        self._configuration_service = ConfigurationService()
        self._file_storage: Optional[FileStoragePort] = None
        self._pdf_processor: Optional[PdfProcessorPort] = None
        self._quality_evaluator: Optional[QualityEvaluatorPort] = None
        self._text_extractor: Optional[TextExtractorPort] = None
        self._obfuscation_service: Optional[DocumentObfuscationService] = None
        self._error_handler: Optional[ErrorHandler] = None
    
    def get_file_storage(self) -> FileStoragePort:
        """Get or create file storage adapter."""
        if self._file_storage is None:
            from ..adapters.local_storage_adapter import LocalStorageAdapter
            self._file_storage = LocalStorageAdapter()
        return self._file_storage
    
    def get_pdf_processor(self, engine: str = "pymupdf") -> PdfProcessorPort:
        """Get or create PDF processor for the specified engine."""
        if self._pdf_processor is None or engine != getattr(self._pdf_processor, '_current_engine', None):
            from ..adapters.pdf_processor_factory import PdfProcessorFactory
            factory = PdfProcessorFactory()
            self._pdf_processor = factory.create_processor(engine, self.get_file_storage())
            # Store current engine for future reference
            setattr(self._pdf_processor, '_current_engine', engine)
        return self._pdf_processor
    
    def get_text_extractor(self, extractor_type: str = "tesseract") -> TextExtractorPort:
        """Get or create text extractor of the specified type."""
        if self._text_extractor is None or extractor_type != getattr(self._text_extractor, '_current_type', None):
            if extractor_type == "mistral":
                from ..adapters.mistral_text_extractor import MistralTextExtractor
                self._text_extractor = MistralTextExtractor(self.get_file_storage())
            else:  # default to tesseract
                from ..adapters.tesseract_text_extractor import TesseractTextExtractor
                self._text_extractor = TesseractTextExtractor(self.get_file_storage())
            setattr(self._text_extractor, '_current_type', extractor_type)
        return self._text_extractor
    
    def get_quality_evaluator(self, extractor_type: str = "tesseract") -> QualityEvaluatorPort:
        """Get or create quality evaluator with the specified text extractor."""
        if self._quality_evaluator is None or extractor_type != getattr(self._quality_evaluator, '_current_extractor_type', None):
            text_extractor = self.get_text_extractor(extractor_type)
            self._quality_evaluator = QualityEvaluationService(text_extractor)
            setattr(self._quality_evaluator, '_current_extractor_type', extractor_type)
        return self._quality_evaluator
    
    def get_obfuscation_service(self) -> DocumentObfuscationService:
        """Get or create document obfuscation service."""
        if self._obfuscation_service is None:
            self._obfuscation_service = DocumentObfuscationService()
        return self._obfuscation_service
    
    def get_error_handler(self) -> ErrorHandler:
        """Get or create error handler."""
        if self._error_handler is None:
            obfuscation_service = self.get_obfuscation_service()
            self._error_handler = ErrorHandler(obfuscation_service)
        return self._error_handler
    
    def get_configuration_service(self) -> ConfigurationService:
        """Get configuration service."""
        return self._configuration_service
    
    def reset(self):
        """Reset all dependencies (useful for testing)."""
        self._file_storage = None
        self._pdf_processor = None
        self._quality_evaluator = None
        self._text_extractor = None
        self._obfuscation_service = None
        self._error_handler = None
