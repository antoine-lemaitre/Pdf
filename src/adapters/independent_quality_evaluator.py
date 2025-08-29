"""
Independent quality evaluator adapter.
Uses different libraries than the obfuscation engines to avoid bias.
"""
import re
import io
from tarfile import LNKTYPE
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pdf2image import convert_from_bytes
import pytesseract

from ..ports.quality_evaluator_port import QualityEvaluatorPort
from ..domain.entities import Document
from ..domain.exceptions import DocumentProcessingError


@dataclass
class TextExtractionResult:
    """Result of text extraction from a document."""
    text: str
    page_count: int
    word_count: int
    pages: List[str]
    execution_time: float = 0.0


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
        """Evaluate if all target terms were properly obfuscated."""
        # Extract text from both documents
        original_extraction = self._extract_text_with_ocr(original_document)
        obfuscated_extraction = self._extract_text_with_ocr(obfuscated_document)
        
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
                "original_ocr_time": original_extraction.execution_time,
                "obfuscated_ocr_time": obfuscated_extraction.execution_time
            }
        }
    
    def evaluate_precision(
        self, 
        original_document: Document, 
        obfuscated_document: Document, 
        terms_to_obfuscate: List[str]
    ) -> Dict[str, Any]:
        """
        Evaluate if only target terms were obfuscated (no false positives).
        
        Strategy: Compare original vs obfuscated document by checking word presence in order.
        For each word in original, check if it's present in obfuscated starting from the last found position.
        """
        try:
            # Extract text from both documents
            original_text_result = self._extract_text_with_ocr(original_document)
            obfuscated_text_result = self._extract_text_with_ocr(obfuscated_document)
            
            # Split texts into words
            original_words = re.findall(r'\b\w+\b', original_text_result.text.lower())
            obfuscated_words = re.findall(r'\b\w+\b', obfuscated_text_result.text.lower())
            
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
                        current_search_position = i + 1  # Start next search from position after found word
                        break
                
                # If word not found, add to missing words list
                if not word_found:
                    missing_words.append(original_word)
            
            # Filter out intentionally obfuscated terms from false positives
            # Create a list of target terms to obfuscate (lowercase for comparison)
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
                    "original_word_count": original_text_result.word_count,
                    "obfuscated_word_count": obfuscated_text_result.word_count,
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
        """Extract text from PDF using OCR with improved configuration."""
        start_time = time.time()
        try:
            pdf_content = self._file_storage.read_file(document.path)
            
            # Convert PDF to images with optimal resolution for OCR
            images = self._pdf2image(pdf_content, dpi=400)  # Good balance between quality and performance
            
            # Extract text from all pages using Tesseract with optimized settings
            pages = []
            full_text = ""
            
            for image in images:
                # Configure Tesseract for better text recognition
                custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1 -c textord_heavy_nr=1 -c textord_min_linesize=2'
                
                page_text = self._pytesseract.image_to_string(
                    image,
                    lang='eng',
                    config=custom_config
                )
                
                pages.append(page_text)
                full_text += page_text + " "
            
            # Clean up text
            full_text = re.sub(r'\s+', ' ', full_text).strip()
            word_count = len(full_text.split())
            
            execution_time = time.time() - start_time
            
            return TextExtractionResult(
                text=full_text,
                page_count=len(pages),
                word_count=word_count,
                pages=pages,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            raise DocumentProcessingError(f"Error extracting text with OCR: {str(e)}")
    
    def _find_terms_in_text(self, text: str, terms: List[str]) -> List[str]:
        """Find which terms appear in the text."""
        found_terms = []
        text_lower = text.lower()
        
        for term in terms:
            if term.lower() in text_lower:
                found_terms.append(term)
        
        return found_terms
    

    
    def _convert_pdf_to_images(self, document: Document):
        """Convert PDF to images for visual comparison."""
        pdf_content = self._file_storage.read_file(document.path)
        return self._pdf2image(pdf_content) 

 