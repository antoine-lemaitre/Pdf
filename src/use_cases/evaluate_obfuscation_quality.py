"""
Use case for evaluating obfuscation quality.
"""
from typing import List

from src.domain.entities import Document, QualityReport
from src.domain.services import QualityEvaluationService
from src.ports.quality_evaluator_port import QualityEvaluatorPort
from src.ports.file_storage_port import FileStoragePort
from src.domain.exceptions import DocumentProcessingError


class EvaluateObfuscationQualityUseCase:
    """Use case for evaluating the quality of obfuscation."""
    
    def __init__(
        self,
        quality_evaluator: QualityEvaluatorPort,
        file_storage: FileStoragePort,
        quality_service: QualityEvaluationService
    ):
        self._quality_evaluator = quality_evaluator
        self._file_storage = file_storage
        self._quality_service = quality_service
    
    def execute(
        self, 
        original_document_path: str, 
        obfuscated_document_path: str, 
        terms_to_obfuscate: List[str],
        engine_used: str = "unknown"
    ) -> QualityReport:
        """
        Execute quality evaluation.
        
        Args:
            original_document_path: Path to the original PDF document
            obfuscated_document_path: Path to the obfuscated PDF document
            terms_to_obfuscate: List of terms that should have been obfuscated
            engine_used: The obfuscation engine that was used
            
        Returns:
            QualityReport: Complete quality evaluation report
            
        Raises:
            DocumentProcessingError: In case of processing error
        """
        try:
            # Validate inputs
            if not original_document_path or not obfuscated_document_path:
                raise DocumentProcessingError("Both original and obfuscated document paths must be provided")
            
            if not terms_to_obfuscate:
                raise DocumentProcessingError("At least one term must be specified for evaluation")
            
            # Check that files exist
            if not self._file_storage.file_exists(original_document_path):
                raise DocumentProcessingError(f"Original document {original_document_path} does not exist")
            
            if not self._file_storage.file_exists(obfuscated_document_path):
                raise DocumentProcessingError(f"Obfuscated document {obfuscated_document_path} does not exist")
            
            # Create document objects
            original_document = Document(path=original_document_path)
            obfuscated_document = Document(path=obfuscated_document_path)
            
            # Extract documents once (mutualized)
            original_extraction, obfuscated_extraction = self._quality_evaluator._extract_documents_once(original_document, obfuscated_document)
            
            # Evaluate completeness
            completeness_result = self._quality_evaluator.evaluate_completeness(
                original_document, obfuscated_document, terms_to_obfuscate
            )
            
            # Evaluate precision (pass extractions to avoid duplication)
            precision_result = self._quality_evaluator.evaluate_precision(
                original_document, obfuscated_document, terms_to_obfuscate,
                original_extraction, obfuscated_extraction
            )
            
            # Evaluate visual integrity
            visual_integrity_result = self._quality_evaluator.evaluate_visual_integrity(
                original_document, obfuscated_document
            )
            
            # Combine all details
            all_details = {
                "completeness": completeness_result,
                "precision": precision_result,
                "visual_integrity": visual_integrity_result
            }
            
            # Create quality report
            report = self._quality_service.create_quality_report(
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