"""
Port for quality evaluation of PDF obfuscation.
This is an interface that defines how the domain can interact with quality evaluators.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any

from ..domain.entities import Document


class QualityEvaluatorPort(ABC):
    """Interface for quality evaluation operations."""
    
    @abstractmethod
    def evaluate_completeness(
        self, 
        original_document: Document, 
        obfuscated_document: Document, 
        terms_to_obfuscate: List[str]
    ) -> Dict[str, Any]:
        """
        Evaluate if all target terms were properly obfuscated.
        
        Args:
            original_document: The original PDF document
            obfuscated_document: The obfuscated PDF document
            terms_to_obfuscate: List of terms that should have been obfuscated
            
        Returns:
            Dictionary with completeness metrics and details
        """
        pass
    
    @abstractmethod
    def evaluate_precision(
        self, 
        original_document: Document, 
        obfuscated_document: Document, 
        terms_to_obfuscate: List[str]
    ) -> Dict[str, Any]:
        """
        Evaluate if only target terms were obfuscated (no false positives).
        
        Args:
            original_document: The original PDF document
            obfuscated_document: The obfuscated PDF document
            terms_to_obfuscate: List of terms that should have been obfuscated
            
        Returns:
            Dictionary with precision metrics and details
        """
        pass
    
    @abstractmethod
    def evaluate_visual_integrity(
        self, 
        original_document: Document, 
        obfuscated_document: Document
    ) -> Dict[str, Any]:
        """
        Evaluate if the visual appearance and layout are preserved.
        
        Args:
            original_document: The original PDF document
            obfuscated_document: The obfuscated PDF document
            
        Returns:
            Dictionary with visual integrity metrics and details
        """
        pass
    
    @abstractmethod
    def get_evaluator_info(self) -> Dict[str, Any]:
        """
        Get information about this quality evaluator.
        
        Returns:
            Dictionary with evaluator information (name, version, capabilities, etc.)
        """
        pass 