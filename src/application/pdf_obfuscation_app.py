"""
Application service for PDF obfuscation.
Coordinates domain services, use cases, and infrastructure adapters.
"""
from typing import List, Optional

from src.domain.entities import ObfuscationRequest, ObfuscationResult, Document, Term, QualityReport
from src.domain.services.document_obfuscation_service import DocumentObfuscationService
from src.domain.exceptions import ObfuscationError, DocumentProcessingError, FileStorageError
from src.domain.services.error_handler import ErrorContext
# Use cases supprimés - logique intégrée directement dans l'application
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
        
        # Use cases supprimés - logique intégrée directement dans les méthodes
    

    
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
            
            # Execute obfuscation directly (use case logic integrated)
            result = self._execute_obfuscation(processor, file_storage, obfuscation_service, source_path, [term.text for term in term_objects], dest_path)
            
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
        engine_used: str = "unknown",
        evaluator_type: str = "tesseract"
    ) -> QualityReport:
        """
        Evaluate the quality of obfuscation for a given document.
        
        Args:
            original_document_path: Path to the original PDF
            obfuscated_document_path: Path to the obfuscated PDF
            terms_to_obfuscate: List of terms that should have been obfuscated
            engine_used: The obfuscation engine that was used
            evaluator_type: Type of evaluator to use (tesseract or mistral)
            
        Returns:
            QualityReport: Complete quality evaluation report
        """
        try:
            # Get quality evaluator and file storage from container
            quality_evaluator = self._dependency_container.get_quality_evaluator(evaluator_type)
            file_storage = self._dependency_container.get_file_storage()
            
            # Execute quality evaluation directly (use case logic integrated)
            return self._execute_quality_evaluation(
                quality_evaluator=quality_evaluator,
                file_storage=file_storage,
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
    
    def _execute_obfuscation(
        self,
        processor: PdfProcessorPort,
        file_storage: FileStoragePort,
        obfuscation_service: DocumentObfuscationService,
        source_path: str,
        terms: List[str],
        dest_path: str
    ) -> ObfuscationResult:
        """Execute obfuscation logic (replaces ObfuscateDocumentUseCase)."""
        try:
            # Create document
            document = Document(path=source_path)
            
            # Create Term objects
            term_objects = [Term(text=term) for term in terms]
            
            # Extract occurrences for all terms
            all_occurrences = []
            for term in term_objects:
                occurrences = processor.extract_text_occurrences(document, term)
                all_occurrences.extend(occurrences)
            
            # Create results by term
            term_results = obfuscation_service.create_term_results(term_objects, all_occurrences)
            
            if all_occurrences:
                # Obfuscate document
                obfuscated_content = processor.obfuscate_occurrences(document, all_occurrences)
                
                # Save obfuscated document
                file_storage.write_file(dest_path, obfuscated_content)
                output_document = Document(path=dest_path)
                
                # Create success result
                result = obfuscation_service.create_success_result(
                    output_document=output_document,
                    term_results=term_results,
                    engine=self._get_engine_name(processor)
                )
            else:
                # No occurrences found
                result = obfuscation_service.create_error_result(
                    error="No terms found in the document",
                    term_results=term_results,
                    engine=self._get_engine_name(processor)
                )
            
            return result
            
        except Exception as e:
            raise DocumentProcessingError(f"Error during document obfuscation {source_path}: {str(e)}")
    
    def _execute_quality_evaluation(
        self,
        quality_evaluator: QualityEvaluatorPort,
        file_storage: FileStoragePort,
        original_document_path: str,
        obfuscated_document_path: str,
        terms_to_obfuscate: List[str],
        engine_used: str
    ) -> QualityReport:
        """Execute quality evaluation logic (replaces EvaluateObfuscationQualityUseCase)."""
        try:
            # Validate inputs
            if not original_document_path or not obfuscated_document_path:
                raise DocumentProcessingError("Both original and obfuscated document paths must be provided")
            
            if not terms_to_obfuscate:
                raise DocumentProcessingError("At least one term must be specified for evaluation")
            
            # Check that files exist
            if not file_storage.file_exists(original_document_path):
                raise DocumentProcessingError(f"Original document {original_document_path} does not exist")
            
            if not file_storage.file_exists(obfuscated_document_path):
                raise DocumentProcessingError(f"Obfuscated document {obfuscated_document_path} does not exist")
            
            # Create document objects
            original_document = Document(path=original_document_path)
            obfuscated_document = Document(path=obfuscated_document_path)
            
            # Evaluate completeness
            completeness_result = quality_evaluator.evaluate_completeness(
                original_document, obfuscated_document, terms_to_obfuscate
            )
            
            # Evaluate precision
            precision_result = quality_evaluator.evaluate_precision(
                original_document, obfuscated_document, terms_to_obfuscate
            )
            
            # Evaluate visual integrity
            visual_integrity_result = quality_evaluator.evaluate_visual_integrity(
                original_document, obfuscated_document
            )
            
            # Combine all details
            all_details = {
                "completeness": completeness_result,
                "precision": precision_result,
                "visual_integrity": visual_integrity_result
            }
            
            # Create quality report using the quality evaluation service
            from src.domain.services.quality_evaluation_service import QualityEvaluationService
            quality_service = QualityEvaluationService(quality_evaluator._text_extractor)
            report = quality_service.create_quality_report(
                original_document_path=original_document_path,
                obfuscated_document_path=obfuscated_document_path,
                terms_to_obfuscate=terms_to_obfuscate,
                engine_used=engine_used,
                completeness_score=completeness_result["score"],
                precision_score=precision_result["score"],
                visual_integrity_score=visual_integrity_result["score"],
                details=all_details
            )
            
            return report
            
        except Exception as e:
            raise DocumentProcessingError(f"Error during quality evaluation: {str(e)}")
    
    def _get_engine_name(self, processor: PdfProcessorPort) -> str:
        """Get the name of the current PDF processor engine."""
        try:
            engine_info = processor.get_engine_info()
            return engine_info.get("name", "unknown")
        except:
            return "unknown" 