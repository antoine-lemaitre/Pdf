"""
Domain services for PDF obfuscation.
Pure business logic without external dependencies.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime

from .entities import (
    Term, TermResult, TermOccurrence, ProcessingStatus,
    ObfuscationRequest, ObfuscationResult, Document,
    QualityMetrics, QualityReport
)
from .exceptions import ObfuscationError


class DocumentObfuscationService:
    """
    Core domain service for document obfuscation business logic.
    This service contains pure business rules and doesn't depend on external systems.
    """
    
    def create_term_results(self, terms: List[Term], occurrences: List[TermOccurrence]) -> List[TermResult]:
        """
        Create term results from found occurrences.
        
        Args:
            terms: List of terms that were searched for
            occurrences: List of all occurrences found
            
        Returns:
            List of term results with their processing status
        """
        term_results = []
        
        for term in terms:
            # Find occurrences for this specific term
            term_occurrences = [occ for occ in occurrences if occ.term.text.lower() == term.text.lower()]
            
            if term_occurrences:
                status = ProcessingStatus.SUCCESS
                message = f"Found {len(term_occurrences)} occurrences"
            else:
                status = ProcessingStatus.NOT_FOUND
                message = "Term not found"
            
            term_result = TermResult(
                term=term,
                status=status,
                occurrences=term_occurrences,
                message=message
            )
            term_results.append(term_result)
        
        return term_results
    
    def validate_obfuscation_request(self, request: ObfuscationRequest) -> None:
        """
        Validate an obfuscation request according to business rules.
        
        Args:
            request: The obfuscation request to validate
            
        Raises:
            ObfuscationError: If the request is invalid
        """
        # Business rule: Must have at least one term
        if not request.terms_to_obfuscate:
            raise ObfuscationError("Must specify at least one term to obfuscate")
        
        # Business rule: All terms must be non-empty
        for term in request.terms_to_obfuscate:
            if not term.text.strip():
                raise ObfuscationError("All terms must be non-empty")
        
        # Business rule: Source and destination cannot be the same
        if request.source_document.path == request.destination_path:
            raise ObfuscationError("Source and destination paths cannot be the same")
    
    def calculate_obfuscation_metrics(self, term_results: List[TermResult]) -> tuple[int, int]:
        """
        Calculate obfuscation metrics from term results.
        
        Args:
            term_results: List of term processing results
            
        Returns:
            Tuple of (total_terms_processed, total_occurrences_obfuscated)
        """
        total_terms_processed = len(term_results)
        total_occurrences_obfuscated = sum(
            result.occurrences_count for result in term_results if result.was_found
        )
        
        return total_terms_processed, total_occurrences_obfuscated
    
    def create_success_result(
        self, 
        output_document: Document, 
        term_results: List[TermResult],
        engine: str
    ) -> ObfuscationResult:
        """
        Create a successful obfuscation result.
        
        Args:
            output_document: The obfuscated output document
            term_results: Results for each term processed
            engine: The engine used for obfuscation
            
        Returns:
            Successful obfuscation result
        """
        total_terms_processed, total_occurrences_obfuscated = self.calculate_obfuscation_metrics(term_results)
        
        return ObfuscationResult(
            success=True,
            output_document=output_document,
            term_results=term_results,
            total_terms_processed=total_terms_processed,
            total_occurrences_obfuscated=total_occurrences_obfuscated,
            message=f"Obfuscation completed successfully using {engine}",
            error=None
        )
    
    def create_error_result(
        self, 
        error: str, 
        term_results: Optional[List[TermResult]] = None,
        engine: str = "unknown"
    ) -> ObfuscationResult:
        """
        Create an error obfuscation result.
        
        Args:
            error: The error message
            term_results: Partial results if any processing was done
            engine: The engine that was being used
            
        Returns:
            Error obfuscation result
        """
        term_results = term_results or []
        total_terms_processed, total_occurrences_obfuscated = self.calculate_obfuscation_metrics(term_results)
        
        return ObfuscationResult(
            success=False,
            output_document=None,
            term_results=term_results,
            total_terms_processed=total_terms_processed,
            total_occurrences_obfuscated=0,  # No actual obfuscation on error
            message=f"Obfuscation failed using {engine}",
            error=error
        )


class QualityEvaluationService:
    """
    Core domain service for quality evaluation business logic.
    This service contains pure business rules for quality assessment.
    """
    
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
        # Business rule: Completeness is most important (40%), then precision (35%), then visual integrity (25%)
        weights = {
            'completeness': 0.4,
            'precision': 0.35,
            'visual_integrity': 0.25
        }
        
        overall_score = (
            completeness_score * weights['completeness'] +
            precision_score * weights['precision'] +
            visual_integrity_score * weights['visual_integrity']
        )
        
        return round(overall_score, 3)
    
    def generate_recommendations(
        self, 
        completeness_score: float, 
        precision_score: float, 
        visual_integrity_score: float
    ) -> List[str]:
        """
        Generate recommendations based on quality scores.
        
        Args:
            completeness_score: Score for completeness
            precision_score: Score for precision
            visual_integrity_score: Score for visual integrity
            
        Returns:
            List of recommendations
        """
        return []
    
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
    ) -> QualityReport:
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
        overall_score = self.calculate_overall_score(completeness_score, precision_score, visual_integrity_score)
        recommendations = self.generate_recommendations(completeness_score, precision_score, visual_integrity_score)
        
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
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        ) 