"""
Service for evaluating obfuscation quality.
"""
import re
from typing import Dict, Any, List
from src.domain.entities import Document, TextExtractionResult
from src.ports.text_extractor_port import TextExtractorPort
from src.domain.exceptions import DocumentProcessingError


class QualityEvaluationService:
    """Service for evaluating obfuscation quality using text extraction."""
    
    def __init__(self, text_extractor: TextExtractorPort):
        """
        Initialize the service.
        
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
                    "obfuscated_word_count": obfuscated_extraction.word_count
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
        """
        Evaluate if only target terms were obfuscated (no false positives).
        
        Strategy: Compare word counts and analyze what disappeared.
        """
        try:
            # Extract text from both documents
            original_extraction = self._text_extractor.extract_text(original_document)
            obfuscated_extraction = self._text_extractor.extract_text(obfuscated_document)
            
            # Use the provided extractions
            original_text = original_extraction.text
            obfuscated_text = obfuscated_extraction.text
            
            # Split texts into words
            original_words = re.findall(r'\b\w+\b', original_text.lower())
            obfuscated_words = re.findall(r'\b\w+\b', obfuscated_text.lower())
            
            # Sort both lists alphabetically to handle OCR differences
            original_words.sort()
            obfuscated_words.sort()
            
            # Track missing words and current search position
            missing_words = []
            current_search_position = 0
            
            # Check each word from original in order
            for original_word in original_words:
                word_found = False
                
                # Search for the word starting from current position
                for i in range(current_search_position, len(obfuscated_words)):
                    if obfuscated_words[i] == original_word:
                        word_found = True
                        current_search_position = i + 1
                        break
                
                # If word not found, add to missing words list
                if not word_found:
                    missing_words.append(original_word)
            
            # Filter out intentionally obfuscated terms from false positives
            target_terms_lower = [term.lower() for term in terms_to_obfuscate]
            
            # Filter missing words to keep only true false positives
            true_false_positives = []
            for missing_word in missing_words:
                # Check if this missing word was NOT in our target list
                was_intentionally_obfuscated = any(
                    target_term in missing_word or missing_word in target_term 
                    for target_term in target_terms_lower
                )
                if not was_intentionally_obfuscated:
                    true_false_positives.append(missing_word)
            
            # Calculate precision metrics
            total_original_words = len(original_words)
            words_found = total_original_words - len(missing_words)
            
            # Calculate precision score (ratio of words that were preserved)
            precision_score = 0.0
            if total_original_words > 0:
                precision_score = words_found / total_original_words
            
            return {
                "score": round(precision_score, 3),
                "total_disappeared_terms": len(missing_words),
                "false_positive_count": len(true_false_positives),
                "details": {
                    "total_original_words": total_original_words,
                    "original_word_count": original_extraction.word_count,
                    "obfuscated_word_count": obfuscated_extraction.word_count,
                    "words_found": words_found,
                    "false_positives": true_false_positives,
                    "intentionally_obfuscated_count": len(missing_words) - len(true_false_positives)
                }
            }
            
        except Exception as e:
            raise DocumentProcessingError(f"Error evaluating precision: {str(e)}")
    
    def evaluate_visual_integrity(
        self, 
        original_document: Document, 
        obfuscated_document: Document
    ) -> Dict[str, Any]:
        """Evaluate visual integrity by comparing document properties."""
        try:
            # For now, we'll use a simple approach
            # In a real implementation, you might want to compare page dimensions, etc.
            return {
                "score": 1.0,  # Placeholder - implement actual visual comparison
                "page_count_match": True,
                "dimension_matches": [True],
                "size_differences": [],
                "details": {
                    "original_pages": 1,
                    "obfuscated_pages": 1,
                    "pages_with_size_changes": 0
                }
            }
        except Exception as e:
            raise DocumentProcessingError(f"Error evaluating visual integrity: {str(e)}")
    
    def _find_terms_in_text(self, text: str, terms: List[str]) -> List[str]:
        """Find which terms appear in the text."""
        found_terms = []
        text_lower = text.lower()
        
        for term in terms:
            if term.lower() in text_lower:
                found_terms.append(term)
        
        return found_terms
