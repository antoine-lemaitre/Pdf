"""
Quality evaluator adapter.
Implements quality evaluation logic using text extractors.
"""
import re
from typing import List, Dict, Any, Optional
from ..ports.quality_evaluator_port import QualityEvaluatorPort
from ..ports.text_extractor_port import TextExtractorPort
from ..domain.entities import Document
from ..domain.exceptions import DocumentProcessingError


class QualityEvaluator(QualityEvaluatorPort):
    """
    Quality evaluator adapter.
    Implements quality evaluation logic using TextExtractorPort.
    """
    
    def __init__(self, text_extractor: TextExtractorPort):
        """
        Initialize the evaluator.
        
        Args:
            text_extractor: Text extractor to use for OCR
        """
        self._text_extractor = text_extractor
    
    def evaluate_completeness(
        self, 
        original_document: Document, 
        obfuscated_document: Document, 
        terms_to_obfuscate: List[str]
    ) -> Dict[str, Any]:
        """Evaluate if all target terms were properly obfuscated."""
        try:
            # Extract text from both documents
            original_extraction = self._text_extractor.extract_text(original_document)
            obfuscated_extraction = self._text_extractor.extract_text(obfuscated_document)
            
            # Find terms in original document
            original_terms = self._find_terms_in_text(original_extraction.text, terms_to_obfuscate)
            
            # Find terms in obfuscated document
            obfuscated_terms = self._find_terms_in_text(obfuscated_extraction.text, terms_to_obfuscate)
            
            # Calculate completeness
            total_terms_found = len(original_terms)
            successfully_obfuscated = total_terms_found - len(obfuscated_terms)
            completeness_score = successfully_obfuscated / total_terms_found if total_terms_found > 0 else 1.0
            
            return {
                "score": completeness_score,
                "total_terms_found": total_terms_found,
                "successfully_obfuscated": successfully_obfuscated,
                "remaining_terms": obfuscated_terms,
                "obfuscated_terms_list": obfuscated_terms,
                "details": {
                    "original_terms": original_terms,
                    "obfuscated_terms": obfuscated_terms,
                    "original_word_count": original_extraction.word_count,
                    "obfuscated_word_count": obfuscated_extraction.word_count,
                    "original_ocr_time": f"{original_extraction.execution_time:.3f}s",
                    "obfuscated_ocr_time": f"{obfuscated_extraction.execution_time:.3f}s"
                }
            }
        except Exception as e:
            raise DocumentProcessingError(f"Error evaluating completeness: {str(e)}")
    
    def evaluate_precision(
        self, 
        original_document: Document, 
        obfuscated_document: Document, 
        terms_to_obfuscate: List[str]
    ) -> Dict[str, Any]:
        """Evaluate if only target terms were obfuscated (no false positives)."""
        try:
            # Try to use extractor annotations if available (for Mistral)
            annotation_result = self._evaluate_with_annotations()
            if annotation_result:
                return annotation_result
            
            # Fallback to manual evaluation
            return self._evaluate_precision_manually(original_document, obfuscated_document, terms_to_obfuscate)
        except Exception as e:
            raise DocumentProcessingError(f"Error evaluating precision: {str(e)}")
    
    def evaluate_visual_integrity(
        self, 
        original_document: Document, 
        obfuscated_document: Document
    ) -> Dict[str, Any]:
        """Evaluate visual integrity by comparing document properties."""
        try:
            # Extract text from both documents to get page counts
            original_extraction = self._text_extractor.extract_text(original_document)
            obfuscated_extraction = self._text_extractor.extract_text(obfuscated_document)
            
            # Compare page counts
            original_pages = original_extraction.page_count
            obfuscated_pages = obfuscated_extraction.page_count
            page_count_match = original_pages == obfuscated_pages
            
            # For now, we assume visual integrity is preserved if page count matches
            # In a more sophisticated implementation, we could compare dimensions, etc.
            visual_integrity_score = 1.0 if page_count_match else 0.0
            
            return {
                "score": visual_integrity_score,
                "page_count_match": page_count_match,
                "dimension_matches": [page_count_match],  # Simplified for now
                "size_differences": [],  # Could be implemented with more sophisticated analysis
                "details": {
                    "original_pages": original_pages,
                    "obfuscated_pages": obfuscated_pages,
                    "pages_with_size_changes": 0 if page_count_match else abs(original_pages - obfuscated_pages)
                }
            }
        except Exception as e:
            raise DocumentProcessingError(f"Error evaluating visual integrity: {str(e)}")
    
    def get_evaluator_info(self) -> Dict[str, Any]:
        """Get information about this quality evaluator."""
        return {
            "name": "quality_evaluator",
            "version": "1.0.0",
            "capabilities": ["completeness", "precision", "visual_integrity"],
            "method": "Direct implementation using TextExtractorPort",
            "text_extractor": self._text_extractor.get_extractor_info()
        }
    
    def _find_terms_in_text(self, text: str, terms: List[str]) -> List[str]:
        """Find terms in text using case-insensitive search."""
        found_terms = []
        text_lower = text.lower()
        
        for term in terms:
            if term.lower() in text_lower:
                found_terms.append(term)
        
        return found_terms
    
    def _evaluate_with_annotations(self) -> Optional[Dict[str, Any]]:
        """Try to evaluate precision using extractor annotations (for Mistral)."""
        try:
            # Check if the text extractor has quality annotations (Mistral specific)
            if hasattr(self._text_extractor, '_last_quality_annotation') and self._text_extractor._last_quality_annotation:
                annotation = self._text_extractor._last_quality_annotation
                
                # Handle both dict and Pydantic model formats
                if hasattr(annotation, 'model_dump'):
                    annotation_dict = annotation.model_dump()
                elif isinstance(annotation, dict):
                    annotation_dict = annotation
                else:
                    return None
                
                # Safely extract values with fallbacks
                obfuscation_analysis = annotation_dict.get("obfuscation_analysis", {})
                quality_metrics = annotation_dict.get("quality_metrics", {})
                
                precision_score = obfuscation_analysis.get("precision_score", 0.0)
                missing_words_count = obfuscation_analysis.get("missing_words_count", 0)
                preserved_words_count = obfuscation_analysis.get("preserved_words_count", 0)
                total_words = quality_metrics.get("total_words", 0)
                
                return {
                    "score": precision_score,
                    "total_disappeared_terms": missing_words_count,
                    "false_positive_count": 0,
                    "total_original_words": total_words,
                    "words_found": preserved_words_count,
                    "details": {
                        "total_original_words": total_words,
                        "original_word_count": total_words,
                        "obfuscated_word_count": total_words - missing_words_count,
                        "words_found": preserved_words_count,
                        "false_positives": [],
                        "intentionally_obfuscated_count": 0,
                        "extractor_annotation": annotation_dict,
                        "mistral_processing_mode": annotation_dict.get("processing_mode", "unknown")
                    }
                }
        except Exception:
            # If anything goes wrong with annotations, fall back to manual evaluation
            pass
        
        return None
    
    def _evaluate_precision_manually(
        self, 
        original_document: Document, 
        obfuscated_document: Document, 
        terms_to_obfuscate: List[str]
    ) -> Dict[str, Any]:
        """Evaluate precision manually by comparing word counts."""
        try:
            # Extract text from both documents
            original_extraction = self._text_extractor.extract_text(original_document)
            obfuscated_extraction = self._text_extractor.extract_text(obfuscated_document)
            
            # Calculate word count differences
            original_word_count = original_extraction.word_count
            obfuscated_word_count = obfuscated_extraction.word_count
            word_difference = original_word_count - obfuscated_word_count
            
            # Simple precision calculation based on word count difference
            # This is a simplified approach - in reality, we'd need more sophisticated analysis
            if original_word_count > 0:
                precision_score = max(0.0, 1.0 - (word_difference / original_word_count))
            else:
                precision_score = 1.0
            
            return {
                "score": precision_score,
                "total_disappeared_terms": word_difference,
                "false_positive_count": 0,  # Simplified - would need more analysis
                "total_original_words": original_word_count,
                "words_found": obfuscated_word_count,
                "details": {
                    "total_original_words": original_word_count,
                    "original_word_count": original_word_count,
                    "obfuscated_word_count": obfuscated_word_count,
                    "words_found": obfuscated_word_count,
                    "false_positives": [],
                    "intentionally_obfuscated_count": word_difference
                }
            }
        except Exception as e:
            raise DocumentProcessingError(f"Error in manual precision evaluation: {str(e)}")
