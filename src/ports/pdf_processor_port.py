"""
Port for PDF processing operations.
This is an interface that defines how the domain can interact with PDF processors.
"""
from abc import ABC, abstractmethod
from typing import List

from ..domain.entities import Document, Term, TermOccurrence


class PdfProcessorPort(ABC):
    """Interface for PDF processing operations."""
    
    @abstractmethod
    def extract_text_occurrences(self, document: Document, term: Term) -> List[TermOccurrence]:
        """
        Extract all occurrences of a term in the document.
        
        Args:
            document: The PDF document to search in
            term: Term to find
            
        Returns:
            List of term occurrences with their positions
            
        Raises:
            DocumentProcessingError: If there's an error processing the document
        """
        pass
    
    @abstractmethod
    def obfuscate_occurrences(self, document: Document, occurrences: List[TermOccurrence]) -> bytes:
        """
        Obfuscate the given term occurrences in the document.
        
        Args:
            document: The source PDF document
            occurrences: List of term occurrences to obfuscate
            
        Returns:
            The obfuscated document content as bytes
            
        Raises:
            DocumentProcessingError: If there's an error processing the document
        """
        pass
    
    @abstractmethod
    def get_engine_info(self) -> dict:
        """
        Get information about this PDF processor engine.
        
        Returns:
            Dictionary with engine information (name, version, features, etc.)
        """
        pass 