"""
Service for evaluating obfuscation quality.
"""
import re
import unicodedata
from typing import Dict, Any, List, Optional
from ..entities import Document, TextExtractionResult
from ...ports.text_extractor_port import TextExtractorPort
from ..exceptions import DocumentProcessingError
from ..quality_annotation_schema import DocumentQualityAnnotation


def normalize_punctuation(text: str) -> str:
    """Normalize all types of apostrophes, quotes and accents to standard characters."""
    # Process each character individually
    result = []
    for char in text:
        # Normalize apostrophes and quotes only for Latin characters
        char = char.replace('\u2019', "'").replace('\u2018', "'").replace('`', "'").replace('´', "'").replace('\u2019', "'")
        char = char.replace('\u201c', '"').replace('\u201d', '"').replace('\u2018', "'").replace('\u2019', "'")
        
        # Apply accent normalization
        normalized = unicodedata.normalize('NFD', char)
        normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        result.append(normalized)

    return ''.join(result)



class QualityEvaluationService:
    """Service for evaluating obfuscation quality using text extraction."""
    
    def __init__(self, text_extractor: TextExtractorPort):
        """
        Initialize the service.
        
        Args:
            text_extractor: Text extractor to use for OCR
        """
        self._text_extractor = text_extractor
    
    def calculate_overall_score(
        self, 
        completeness_score: float, 
        precision_score: float, 
        visual_integrity_score: float
    ) -> float:
        """
        Calculate overall quality score from individual metrics.
        
        Args:
            completeness_score: Score for completeness (0.0 to 1.0)
            precision_score: Score for precision (0.0 to 1.0)
            visual_integrity_score: Score for visual integrity (0.0 to 1.0)
            
        Returns:
            Overall score (0.0 to 1.0)
        """
        # Business rule: Completeness is most important (45%), then precision (45%), then visual integrity (10%)
        weights = {
            'completeness': 0.45,
            'precision': 0.45,
            'visual_integrity': 0.10
        }
        
        overall_score = (
            completeness_score * weights['completeness'] +
            precision_score * weights['precision'] +
            visual_integrity_score * weights['visual_integrity']
        )
        
        return round(overall_score, 3)
    
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
        """
        Evaluate if only target terms were obfuscated (no false positives).
        
        Strategy: Compare word counts and analyze what disappeared.
        """
        try:
            # Extract text from both documents
            original_extraction = self._text_extractor.extract_text(original_document)
            obfuscated_extraction = self._text_extractor.extract_text(obfuscated_document)
            original_text = original_extraction.text
            obfuscated_text = obfuscated_extraction.text
            
            # Split texts into words and clean punctuation
            original_words_raw = original_text.lower().split()
            obfuscated_words_raw = obfuscated_text.lower().split()
            
            # Clean and normalize words
            original_words = [normalize_punctuation(re.sub(r'^[^\w]+|[^\w]+$', '', word)) for word in original_words_raw if re.sub(r'^[^\w]+|[^\w]+$', '', word)]
            obfuscated_words = [normalize_punctuation(re.sub(r'^[^\w]+|[^\w]+$', '', word)) for word in obfuscated_words_raw if re.sub(r'^[^\w]+|[^\w]+$', '', word)]
            
            # Sort both lists alphabetically to handle OCR differences
            original_words.sort()
            obfuscated_words.sort()
            
            # Simple approach: remove found words from obfuscated list
            remaining_words_obfuscated = obfuscated_words.copy()
            remaining_words_original = []
            # For each original word, remove it from remaining words
            for word in original_words:
                if word in remaining_words_obfuscated:
                    remaining_words_obfuscated.remove(word)
                else:
                    remaining_words_original.append(word)
            
            # Missing words are those that remain (not found in original)
            missing_words = remaining_words_original
            
            # Filter out intentionally obfuscated terms from false positives
            target_terms_lower = [normalize_punctuation(term).lower() for term in terms_to_obfuscate]
            
            # Pre-calculate target terms data for efficiency
            target_terms_data = []
            for target_term in target_terms_lower:
                target_terms_data.append({
                    'term': target_term,
                    'words': target_term.split() if ' ' in target_term else [target_term]
                })
            
            # Filter missing words to keep only true false positives
            true_false_positives = []
            targeted_terms_found = []
            for missing_word in missing_words:
                # Check if this missing word was NOT in our target list
                was_intentionally_obfuscated = any(
                    self._is_word_obfuscation_target_optimized(missing_word, target_data)
                    for target_data in target_terms_data
                )
                if not was_intentionally_obfuscated:
                    true_false_positives.append(missing_word)
                else:
                    targeted_terms_found.append(missing_word)
            
            # Calculate precision metrics
            total_original_words = len(original_words)
            words_found = total_original_words - len(missing_words)
            
            # Calculate precision score (ratio of words that were preserved)
            precision_score = 1.0
            if total_original_words > 0:
                precision_score = round(1 - (len(true_false_positives) / total_original_words), 3)
            
            return {
                "score": precision_score,
                "total_disappeared_terms": len(missing_words),
                "false_positive_count": len(true_false_positives),
                "total_original_words": total_original_words,
                "details": {
                    "total_original_words": total_original_words,
                    "targeted_terms_found": targeted_terms_found,
                    "original_word_count": original_extraction.word_count,
                    "obfuscated_word_count": obfuscated_extraction.word_count,
                    "words_found": words_found,
                    "false_positives": true_false_positives,
                    "remaining_words_obfuscated": remaining_words_obfuscated,
                    "intentionally_obfuscated_count": len(targeted_terms_found)
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
    
    def _is_word_obfuscation_target_optimized(self, missing_word: str, target_data: dict) -> bool:
        """
        Check if a missing word was intentionally obfuscated based on pre-calculated target data.
        
        Handles three cases:
        1. Exact match (word or string)
        2. Multi-word string (missing word is part of the string)
        3. Partial word match (missing word is substring of target)
        
        Args:
            missing_word: The word that disappeared from obfuscated document
            target_data: Pre-calculated data with 'term' and 'words' keys
            
        Returns:
            True if the missing word was likely obfuscated as part of the target term
        """
        target_term = target_data['term']
        target_words = target_data['words']
        
        # Normalize missing word to ensure consistent comparison
        missing_word_normalized = normalize_punctuation(missing_word)
        
        # Cas 1: Correspondance exacte (mot entier ou chaîne complète)
        if missing_word_normalized == target_term:
            return True
        
        # Cas 2: Chaîne de caractères - vérifier si le mot fait partie de la chaîne
        if len(target_words) > 1:  # C'est une chaîne multi-mots
            # Normalize all target words for comparison
            target_words_normalized = [normalize_punctuation(word) for word in target_words]
            return missing_word_normalized in target_words_normalized
        
        # Cas 3: Partie d'un mot - vérifier si c'est une sous-chaîne significative
        # Pour les emails, noms, etc. - le mot manquant peut être une partie du terme cible
        if len(missing_word_normalized) >= 2 and missing_word_normalized in target_term:
            return True
        
        return False
    
    def create_quality_report(
        self,
        original_document_path: str,
        obfuscated_document_path: str,
        terms_to_obfuscate: List[str],
        engine_used: str,
        completeness_score: float,
        precision_score: float,
        visual_integrity_score: float,
        details: Dict[str, Any]
    ) -> "QualityReport":
        """
        Create a complete quality report.
        
        Args:
            original_document_path: Path to original document
            obfuscated_document_path: Path to obfuscated document
            terms_to_obfuscate: List of terms that should have been obfuscated
            engine_used: The obfuscation engine used
            completeness_score: Completeness score
            precision_score: Precision score
            visual_integrity_score: Visual integrity score
            details: Additional details for each metric
            
        Returns:
            Complete quality report
        """
        from datetime import datetime
        from ..entities import QualityReport, QualityMetrics
        
        overall_score = self.calculate_overall_score(completeness_score, precision_score, visual_integrity_score)
        
        # Extract detailed term information from completeness and precision details
        non_obfuscated_terms = []
        false_positive_terms = []
        
        # Extract non-obfuscated terms from completeness details
        if 'completeness' in details and 'remaining_terms' in details['completeness']:
            non_obfuscated_terms = details['completeness']['remaining_terms']
        
        # Extract false positive terms from precision details
        if 'precision' in details and 'false_positives' in details['precision']:
            false_positive_terms = details['precision']['false_positives']
        
        metrics = QualityMetrics(
            completeness_score=completeness_score,
            precision_score=precision_score,
            visual_integrity_score=visual_integrity_score,
            overall_score=overall_score,
            details=details,
            non_obfuscated_terms=non_obfuscated_terms,
            false_positive_terms=false_positive_terms
        )
        
        return QualityReport(
            original_document_path=original_document_path,
            obfuscated_document_path=obfuscated_document_path,
            terms_to_obfuscate=terms_to_obfuscate,
            engine_used=engine_used,
            metrics=metrics,
            timestamp=datetime.now().isoformat()
        )
