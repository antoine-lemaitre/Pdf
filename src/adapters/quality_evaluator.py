"""
Quality evaluator adapter.
Uses QualityEvaluationService with text extractors to evaluate obfuscation quality.
"""
from typing import List, Dict, Any
from ..ports.quality_evaluator_port import QualityEvaluatorPort
from ..ports.text_extractor_port import TextExtractorPort
from ..domain.entities import Document
from ..domain.quality_evaluation_service import QualityEvaluationService


class QualityEvaluator(QualityEvaluatorPort):
    """
    Quality evaluator using QualityEvaluationService.
    Delegates text extraction to TextExtractorPort and quality calculation to QualityEvaluationService.
    """
    
    def __init__(self, text_extractor: TextExtractorPort):
        """
        Initialize the evaluator.
        
        Args:
            text_extractor: Text extractor to use for OCR
        """
        self._quality_service = QualityEvaluationService(text_extractor)
    
    def evaluate_completeness(
        self, 
        original_document: Document, 
        obfuscated_document: Document, 
        terms_to_obfuscate: List[str]
    ) -> Dict[str, Any]:
        """Evaluate if all target terms were properly obfuscated."""
        return self._quality_service.evaluate_completeness(original_document, obfuscated_document, terms_to_obfuscate)
    
    def evaluate_precision(
        self, 
        original_document: Document, 
        obfuscated_document: Document, 
        terms_to_obfuscate: List[str]
    ) -> Dict[str, Any]:
        """Evaluate if only target terms were obfuscated (no false positives)."""
        return self._quality_service.evaluate_precision(original_document, obfuscated_document, terms_to_obfuscate)
    
    def evaluate_visual_integrity(
        self, 
        original_document: Document, 
        obfuscated_document: Document
    ) -> Dict[str, Any]:
        """Evaluate visual integrity by comparing document properties."""
        return self._quality_service.evaluate_visual_integrity(original_document, obfuscated_document)
    
    def get_evaluator_info(self) -> Dict[str, Any]:
        """Get information about this quality evaluator."""
        return {
            "name": "quality_evaluator",
            "version": "1.0.0",
            "capabilities": ["completeness", "precision", "visual_integrity"],
            "method": "Uses QualityEvaluationService with TextExtractorPort",
            "text_extractor": self._quality_service._text_extractor.get_extractor_info()
        }
