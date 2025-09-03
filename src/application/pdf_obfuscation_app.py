"""
Application service for PDF obfuscation.
Coordinates domain services, use cases, and infrastructure adapters.
"""
from typing import List, Optional

from src.domain.entities import ObfuscationRequest, ObfuscationResult, Document, Term, QualityReport
from src.domain.exceptions import ObfuscationError, DocumentProcessingError, FileStorageError
from src.use_cases.obfuscate_document import ObfuscateDocumentUseCase
from src.use_cases.evaluate_obfuscation_quality import EvaluateObfuscationQualityUseCase
from src.ports.pdf_processor_port import PdfProcessorPort
from src.ports.file_storage_port import FileStoragePort
from src.ports.quality_evaluator_port import QualityEvaluatorPort
from .dependency_container import DependencyContainer


class PdfObfuscationApplication:
    """Main application service for PDF obfuscation."""
    
    def __init__(
        self,
        dependency_container: Optional[DependencyContainer] = None,
        default_engine: str = "pymupdf"
    ):
        """
        Initialize the application with its dependencies.
        
        Args:
            dependency_container: Container managing all dependencies (default: new instance)
            default_engine: Default engine to use (pymupdf)
        """
        self._dependency_container = dependency_container or DependencyContainer()
        self._default_engine = default_engine
        
        # Initialize use cases
        self._obfuscate_use_case = ObfuscateDocumentUseCase(
            pdf_processor=self._dependency_container.get_pdf_processor(default_engine),
            file_storage=self._dependency_container.get_file_storage(),
            obfuscation_service=self._dependency_container.get_obfuscation_service()
        )
    

    
    def obfuscate_document(
        self,
        source_path: str,
        terms: List[str],
        destination_path: Optional[str] = None,
        engine: str = "pymupdf",
        evaluate_quality: bool = False
    ) -> ObfuscationResult:
        """
        Obfuscate a PDF document with the specified terms.
        
        Args:
            source_path: Path to the source document
            terms: List of terms to obfuscate
            destination_path: Destination path (optional)
            engine: Obfuscation engine to use
            evaluate_quality: Whether to evaluate quality after obfuscation
            
        Returns:
            ObfuscationResult: Obfuscation result
        """
        try:
            # Input validation using configuration service
            config_service = self._dependency_container.get_configuration_service()
            if not source_path or not source_path.strip():
                raise ObfuscationError("Source document path cannot be empty")
            
            if not terms:
                raise ObfuscationError("At least one term must be specified")
            
            if not config_service.validate_engine(engine):
                supported = ", ".join(config_service.get_supported_engines())
                raise ObfuscationError(f"Engine {engine} not supported. Available engines: {supported}")
            
            # Check that source file exists
            file_storage = self._dependency_container.get_file_storage()
            if not file_storage.file_exists(source_path):
                raise ObfuscationError(f"Source file {source_path} does not exist")
            
            # Create obfuscation request
            source_document = Document(path=source_path)
            if destination_path:
                dest_path = destination_path
            else:
                dest_path = config_service.get_default_output_path(source_path)
            term_objects = [Term(text=term.strip()) for term in terms if term.strip()]
            
            request = ObfuscationRequest(
                source_document=source_document,
                destination_path=dest_path,
                terms_to_obfuscate=term_objects,
                engine=engine
            )
            
            # Validate request according to business rules
            obfuscation_service = self._dependency_container.get_obfuscation_service()
            obfuscation_service.validate_obfuscation_request(request)
            
            # Get processor for the specified engine
            processor = self._dependency_container.get_pdf_processor(engine)
            
            # Create use case with the correct processor
            use_case = ObfuscateDocumentUseCase(
                pdf_processor=processor,
                file_storage=file_storage,
                obfuscation_service=obfuscation_service
            )
            
            # Execute use case
            result = use_case.execute(source_path, [term.text for term in term_objects], dest_path)
            
            # Evaluate quality if requested
            if evaluate_quality and result.success:
                quality_report = self.evaluate_quality(source_path, dest_path, terms, engine)
                # Add quality report to the result (you might want to extend ObfuscationResult for this)
                print(f"Quality evaluation completed. Overall score: {quality_report.metrics.overall_score}")
            
            return result
            
        except Exception as e:
            # Use centralized error handler
            # Ensure dest_path is defined for error context
            config_service = self._dependency_container.get_configuration_service()
            dest_path = destination_path or config_service.get_default_output_path(source_path)
            context = ErrorContext(
                operation="obfuscate_document",
                source_path=source_path,
                destination_path=dest_path,
                terms=terms,
                engine=engine
            )
            return self._dependency_container.get_error_handler().handle_obfuscation_error(e, context, engine)
    
    def evaluate_quality(
        self,
        original_document_path: str,
        obfuscated_document_path: str,
        terms_to_obfuscate: List[str],
        engine_used: str = "unknown"
    ) -> QualityReport:
        """
        Evaluate the quality of obfuscation for a given document.
        
        Args:
            original_document_path: Path to the original PDF
            obfuscated_document_path: Path to the obfuscated PDF
            terms_to_obfuscate: List of terms that should have been obfuscated
            engine_used: The obfuscation engine that was used
            
        Returns:
            QualityReport: Complete quality evaluation report
        """
        try:
            # Get quality evaluator and file storage from container
            quality_evaluator = self._dependency_container.get_quality_evaluator("tesseract")  # Default to tesseract
            file_storage = self._dependency_container.get_file_storage()
            
            # Create use case with the quality evaluation service
            from src.domain.services.quality_evaluation_service import QualityEvaluationService
            quality_service = QualityEvaluationService(quality_evaluator._text_extractor)
            evaluate_use_case = EvaluateObfuscationQualityUseCase(
                quality_evaluator=quality_evaluator,
                file_storage=file_storage,
                quality_service=quality_service
            )
            
            return evaluate_use_case.execute(
                original_document_path=original_document_path,
                obfuscated_document_path=obfuscated_document_path,
                terms_to_obfuscate=terms_to_obfuscate,
                engine_used=engine_used
            )
        except Exception as e:
            raise ObfuscationError(f"Error during quality evaluation: {str(e)}")
    
    def get_supported_engines(self) -> List[str]:
        """
        Returns the list of supported obfuscation engines.
        
        Returns:
            List[str]: List of supported engines
        """
        return self._dependency_container.get_configuration_service().get_supported_engines()
    
    def validate_document(self, document_path: str) -> bool:
        """
        Validates that a document can be processed.
        
        Args:
            document_path: Path to the document
            
        Returns:
            bool: True if the document is valid
        """
        try:
            file_storage = self._dependency_container.get_file_storage()
            if not file_storage.file_exists(document_path):
                return False
                
            if not document_path.lower().endswith('.pdf'):
                return False
                
            # Try to open the document with the processor
            document = Document(path=document_path)
            # Basic test - try to extract text
            test_term = Term(text="test")
            pdf_processor = self._dependency_container.get_pdf_processor(self._default_engine)
            pdf_processor.extract_text_occurrences(document, test_term)
            
            return True
            
        except Exception:
            return False 