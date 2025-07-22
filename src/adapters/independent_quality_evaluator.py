"""
Independent quality evaluator adapter.
Uses different libraries than the obfuscation engines to avoid bias.
"""
import re
import io
from typing import List, Dict, Any
from dataclasses import dataclass
from pdf2image import convert_from_bytes
import pytesseract

from ..ports.quality_evaluator_port import QualityEvaluatorPort
from ..domain.entities import Document
from ..domain.exceptions import DocumentProcessingError


@dataclass
class TextExtractionResult:
    """Result of text extraction from a PDF."""
    text: str
    page_count: int
    word_count: int
    pages: List[str]


class IndependentQualityEvaluator(QualityEvaluatorPort):
    """
    Quality evaluator using independent libraries to avoid bias.
    Uses pdf2image + OCR for text extraction and visual comparison.
    """
    
    def __init__(self, file_storage):
        """
        Initialize the evaluator.
        
        Args:
            file_storage: File storage port for reading documents
        """
        self._file_storage = file_storage
        self._pdf2image = convert_from_bytes
        self._pytesseract = pytesseract
    
    def evaluate_completeness(
        self, 
        original_document: Document, 
        obfuscated_document: Document, 
        terms_to_obfuscate: List[str]
    ) -> Dict[str, Any]:
        """
        Evaluate if all target terms were properly obfuscated.
        
        Strategy: Extract text using OCR and compare term presence.
        """
        try:
            # Extract text from both documents using OCR
            original_text_result = self._extract_text_with_ocr(original_document)
            obfuscated_text_result = self._extract_text_with_ocr(obfuscated_document)
            
            # Find terms in original document
            original_terms_found = self._find_terms_in_text(
                original_text_result.text, terms_to_obfuscate
            )
            
            # Find terms in obfuscated document
            obfuscated_terms_found = self._find_terms_in_text(
                obfuscated_text_result.text, terms_to_obfuscate
            )
            
            # Calculate completeness metrics
            total_terms_to_obfuscate = len(original_terms_found)
            successfully_obfuscated = total_terms_to_obfuscate - len(obfuscated_terms_found)
            
            completeness_score = 0.0
            if total_terms_to_obfuscate > 0:
                completeness_score = successfully_obfuscated / total_terms_to_obfuscate
            
            return {
                "score": round(completeness_score, 3),
                "total_terms_found": total_terms_to_obfuscate,
                "successfully_obfuscated": successfully_obfuscated,
                "remaining_terms": obfuscated_terms_found,
                "details": {
                    "original_terms": original_terms_found,
                    "obfuscated_terms": obfuscated_terms_found,
                    "original_word_count": original_text_result.word_count,
                    "obfuscated_word_count": obfuscated_text_result.word_count
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
        
        Strategy: Check if non-target text was accidentally obfuscated.
        """
        try:
            # Extract text from both documents
            original_text_result = self._extract_text_with_ocr(original_document)
            obfuscated_text_result = self._extract_text_with_ocr(obfuscated_document)
            
            # Get common words that should NOT be obfuscated
            non_target_terms = self._get_non_target_terms(original_text_result.text)
            
            # Check if non-target terms were affected
            false_positives = []
            for term in non_target_terms:
                if term in original_text_result.text and term not in obfuscated_text_result.text:
                    false_positives.append(term)
            
            # Calculate precision score
            precision_score = 1.0
            if len(non_target_terms) > 0:
                precision_score = 1.0 - (len(false_positives) / len(non_target_terms))
            
            # Additional check: compare word count reduction
            word_reduction_ratio = 0.0
            if original_text_result.word_count > 0:
                word_reduction_ratio = (
                    original_text_result.word_count - obfuscated_text_result.word_count
                ) / original_text_result.word_count
            
            return {
                "score": round(max(0.0, precision_score), 3),
                "false_positives": false_positives,
                "non_target_terms_checked": len(non_target_terms),
                "word_reduction_ratio": round(word_reduction_ratio, 3),
                "details": {
                    "non_target_terms": non_target_terms[:10],  # Limit for readability
                    "false_positive_count": len(false_positives),
                    "original_word_count": original_text_result.word_count,
                    "obfuscated_word_count": obfuscated_text_result.word_count
                }
            }
            
        except Exception as e:
            raise DocumentProcessingError(f"Error evaluating precision: {str(e)}")
    
    def evaluate_visual_integrity(
        self, 
        original_document: Document, 
        obfuscated_document: Document
    ) -> Dict[str, Any]:
        """
        Evaluate if the visual appearance and layout are preserved.
        
        Strategy: Compare image dimensions and structure.
        """
        try:
            # Convert both documents to images
            original_images = self._convert_pdf_to_images(original_document)
            obfuscated_images = self._convert_pdf_to_images(obfuscated_document)
            
            # Basic structural comparison
            page_count_match = len(original_images) == len(obfuscated_images)
            
            # Compare dimensions of each page
            dimension_matches = []
            size_differences = []
            
            if page_count_match:
                for i, (orig_img, obf_img) in enumerate(zip(original_images, obfuscated_images)):
                    orig_size = orig_img.size
                    obf_size = obf_img.size
                    dimension_match = (orig_size == obf_size)
                    dimension_matches.append(dimension_match)
                    
                    if not dimension_match:
                        size_diff = {
                            'page': i + 1,
                            'original_size': orig_size,
                            'obfuscated_size': obf_size
                        }
                        size_differences.append(size_diff)
            
            # Calculate overall visual integrity score
            visual_score = 0.0
            if page_count_match and dimension_matches:
                visual_score = sum(dimension_matches) / len(dimension_matches)
            
            return {
                "score": round(visual_score, 3),
                "page_count_match": page_count_match,
                "dimension_matches": dimension_matches,
                "size_differences": size_differences,
                "details": {
                    "original_pages": len(original_images),
                    "obfuscated_pages": len(obfuscated_images),
                    "pages_with_size_changes": len(size_differences)
                }
            }
            
        except Exception as e:
            raise DocumentProcessingError(f"Error evaluating visual integrity: {str(e)}")
    
    def get_evaluator_info(self) -> Dict[str, Any]:
        """Get information about this quality evaluator."""
        return {
            "name": "independent_quality_evaluator",
            "version": "1.0.0",
            "capabilities": ["completeness", "precision", "visual_integrity"],
            "method": "Uses pdf2image + OCR for text extraction and visual comparison",
            "bias_avoidance": "Uses different libraries than obfuscation engines (PyMuPDF, PyPDFium2, pdfplumber)"
        }
    
    def _extract_text_with_ocr(self, document: Document) -> TextExtractionResult:
        """Extract text from PDF using OCR."""
        try:
            pdf_content = self._file_storage.read_file(document.path)
            
            # Convert PDF to images
            images = self._pdf2image(pdf_content)
            
            # Extract text from all pages using OCR
            pages = []
            full_text = ""
            
            for image in images:
                page_text = self._pytesseract.image_to_string(image, lang='fra+eng')
                pages.append(page_text)
                full_text += page_text + " "
            
            # Clean up text
            full_text = re.sub(r'\s+', ' ', full_text).strip()
            word_count = len(full_text.split())
            
            return TextExtractionResult(
                text=full_text,
                page_count=len(pages),
                word_count=word_count,
                pages=pages
            )
            
        except Exception as e:
            raise DocumentProcessingError(f"Error extracting text with OCR: {str(e)}")
    
    def _find_terms_in_text(self, text: str, terms: List[str]) -> List[str]:
        """Find which terms appear in the text."""
        found_terms = []
        text_lower = text.lower()
        
        for term in terms:
            if term.lower() in text_lower:
                found_terms.append(term)
        
        return found_terms
    
    def _get_non_target_terms(self, text: str) -> List[str]:
        """Get common words that should NOT be obfuscated."""
        # Common French words that should remain visible
        common_words = [
            "le", "la", "les", "un", "une", "des", "et", "ou", "de", "du", "des",
            "à", "au", "aux", "avec", "sans", "pour", "par", "sur", "sous",
            "je", "tu", "il", "elle", "nous", "vous", "ils", "elles",
            "être", "avoir", "faire", "dire", "aller", "voir", "savoir",
            "nom", "prénom", "adresse", "téléphone", "email", "cv", "curriculum",
            "expérience", "formation", "compétences", "langues", "projet"
        ]
        
        # Find common words that appear in the text
        text_lower = text.lower()
        found_common_words = [word for word in common_words if word in text_lower]
        
        return found_common_words
    
    def _convert_pdf_to_images(self, document: Document):
        """Convert PDF to images for visual comparison."""
        pdf_content = self._file_storage.read_file(document.path)
        return self._pdf2image(pdf_content) 