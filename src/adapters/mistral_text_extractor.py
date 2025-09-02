"""
Mistral text extractor adapter.
Uses Mistral AI OCR for text extraction.
"""
import re
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from mistralai import Mistral
import os

from ..ports.text_extractor_port import TextExtractorPort
from ..domain.entities import Document, TextExtractionResult
from ..domain.exceptions import DocumentProcessingError


class MistralTextExtractor(TextExtractorPort):
    """
    Text extractor using Mistral AI OCR.
    Uses Mistral AI for text extraction.
    """
    
    def __init__(self, file_storage, mistral_api_key: Optional[str] = None):
        """
        Initialize the extractor.
        
        Args:
            file_storage: File storage port for reading documents
            mistral_api_key: API key for Mistral AI (will use env var MISTRAL_API_KEY if not provided)
        """
        self._file_storage = file_storage
        self._mistral_api_key = mistral_api_key or os.getenv("MISTRAL_API_KEY")
        
        if not self._mistral_api_key:
            raise ValueError("Mistral API key is required. Set MISTRAL_API_KEY environment variable or pass it to the constructor.")
        
        # Initialize Mistral client
        self._mistral_client = Mistral(api_key=self._mistral_api_key)
    
    def extract_text(self, document: Document) -> TextExtractionResult:
        """Extract text from PDF using Mistral AI OCR."""
        start_time = time.time()
        try:
            # Read PDF content directly
            pdf_content = self._file_storage.read_file(document.path)
            
            # Extract text directly from PDF using Mistral OCR
            extracted_text = self._extract_text_with_mistral(pdf_content)
            
            # Clean up text
            full_text = re.sub(r'\s+', ' ', extracted_text).strip()
            word_count = len(full_text.split())
            
            execution_time = time.time() - start_time
            
            return TextExtractionResult(
                text=full_text,
                page_count=1,  # Will be updated from response
                word_count=word_count,
                pages=[extracted_text],
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            raise DocumentProcessingError(f"Error extracting text with Mistral OCR: {str(e)}")
    
    def _extract_text_with_mistral(self, pdf_content: bytes) -> str:
        """Extract text from PDF using Mistral AI OCR via official library."""
        try:
            # Encode PDF to base64
            import base64
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            # Call Mistral OCR API directly on PDF
            response = self._mistral_client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "document_url",
                    "document_url": f"data:application/pdf;base64,{pdf_base64}"
                },
                include_image_base64=True
            )
            
            # Extract the text from the OCR response (markdown format)
            extracted_text = ""
            if response.pages:
                for page in response.pages:
                    if hasattr(page, 'markdown'):
                        extracted_text += page.markdown + " "
                    else:
                        # Fallback if markdown not available
                        extracted_text += str(page) + " "
            
            return extracted_text
            
        except Exception as e:
            raise DocumentProcessingError(f"Error extracting text with Mistral OCR: {str(e)}")
    
    def get_extractor_info(self) -> Dict[str, Any]:
        """Get information about this text extractor."""
        return {
            "name": "mistral_text_extractor",
            "version": "1.0.0",
            "method": "Uses Mistral AI OCR for text extraction",
            "bias_avoidance": "Uses different libraries than obfuscation engines (PyMuPDF, PyPDFium2, pdfplumber)"
        }
