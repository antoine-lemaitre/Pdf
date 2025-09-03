"""
Port for text extraction from documents.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from src.domain.entities import Document, TextExtractionResult


class TextExtractorPort(ABC):
    """Port for extracting text from documents using OCR."""
    
    @abstractmethod
    def extract_text(self, document: Document) -> TextExtractionResult:
        """
        Extract text from a document.
        
        Args:
            document: Document to extract text from
            
        Returns:
            TextExtractionResult containing extracted text and metadata
        """
        pass
    
    @abstractmethod
    def get_extractor_info(self) -> dict:
        """Get information about this text extractor."""
        pass
    
    def get_quality_annotation(self) -> Optional[Dict[str, Any]]:
        """
        Get quality annotation if available from the extractor.
        
        Returns:
            Quality annotation data if available, None otherwise.
            This method has a default implementation that returns None,
            allowing extractors to override it if they support annotations.
        """
        return None
