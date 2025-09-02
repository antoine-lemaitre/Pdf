"""
Tesseract text extractor adapter.
Uses Tesseract OCR for text extraction.
"""
import re
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pdf2image import convert_from_bytes
import pytesseract

from ..ports.text_extractor_port import TextExtractorPort
from ..domain.entities import Document, TextExtractionResult
from ..domain.exceptions import DocumentProcessingError


class TesseractTextExtractor(TextExtractorPort):
    """
    Text extractor using Tesseract OCR.
    Uses pdf2image + Tesseract for text extraction.
    """
    
    def __init__(self, file_storage):
        """
        Initialize the extractor.
        
        Args:
            file_storage: File storage port for reading documents
        """
        self._file_storage = file_storage
        self._pdf2image = convert_from_bytes
        self._pytesseract = pytesseract
    
    def extract_text(self, document: Document) -> TextExtractionResult:
        """Extract text from PDF using Tesseract OCR."""
        start_time = time.time()
        try:
            pdf_content = self._file_storage.read_file(document.path)
            
            # Convert PDF to images
            images = self._pdf2image(pdf_content, dpi=400)
            
            # Extract text from all pages using Tesseract
            pages = []
            full_text = ""
            
            for image in images:
                page_text = self._pytesseract.image_to_string(image)
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
            raise DocumentProcessingError(f"Error extracting text with Tesseract OCR: {str(e)}")
    
    def get_extractor_info(self) -> Dict[str, Any]:
        """Get information about this text extractor."""
        return {
            "name": "tesseract_text_extractor",
            "version": "1.0.0",
            "method": "Uses pdf2image + Tesseract OCR for text extraction",
            "bias_avoidance": "Uses different libraries than obfuscation engines (PyMuPDF, PyPDFium2, pdfplumber)"
        }
