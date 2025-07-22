"""
Domain entities for PDF obfuscation.
Pure business objects with no external dependencies.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class ProcessingStatus(Enum):
    """Status of term processing."""
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    ERROR = "error"


@dataclass(frozen=True)
class QualityMetrics:
    """Quality metrics for obfuscation evaluation."""
    completeness_score: float  # 0.0 to 1.0
    precision_score: float     # 0.0 to 1.0
    visual_integrity_score: float  # 0.0 to 1.0
    overall_score: float       # 0.0 to 1.0
    details: Dict[str, Any]
    # New detailed information
    non_obfuscated_terms: List[str]  # Terms that should have been obfuscated but weren't
    false_positive_terms: List[str]  # Terms that were obfuscated by mistake


@dataclass(frozen=True)
class QualityReport:
    """Complete quality evaluation report."""
    original_document_path: str
    obfuscated_document_path: str
    terms_to_obfuscate: List[str]
    engine_used: str
    metrics: QualityMetrics
    recommendations: List[str]
    timestamp: str


@dataclass(frozen=True)
class Term:
    """A term to be obfuscated in a document."""
    text: str
    
    def __post_init__(self):
        if not self.text or not self.text.strip():
            raise ValueError("Term text cannot be empty")


@dataclass(frozen=True)
class Position:
    """Position coordinates in a document."""
    x0: float
    y0: float
    x1: float
    y1: float
    
    def __post_init__(self):
        if self.x0 > self.x1 or self.y0 > self.y1:
            raise ValueError("Invalid position coordinates")


@dataclass(frozen=True)
class TermOccurrence:
    """An occurrence of a term found in a document."""
    term: Term
    position: Position
    page_number: int
    
    def __post_init__(self):
        if self.page_number < 1:
            raise ValueError("Page number must be positive")


@dataclass(frozen=True)
class TermResult:
    """Result of processing a specific term."""
    term: Term
    status: ProcessingStatus
    occurrences: List[TermOccurrence]
    message: str
    
    @property
    def occurrences_count(self) -> int:
        """Number of occurrences found."""
        return len(self.occurrences)
    
    @property
    def was_found(self) -> bool:
        """Whether the term was found in the document."""
        return self.status == ProcessingStatus.SUCCESS and len(self.occurrences) > 0


@dataclass(frozen=True)
class Document:
    """A document to be processed."""
    path: str
    
    def __post_init__(self):
        if not self.path or not self.path.strip():
            raise ValueError("Document path cannot be empty")


@dataclass(frozen=True)
class ObfuscationRequest:
    """Request to obfuscate terms in a document."""
    source_document: Document
    destination_path: str
    terms_to_obfuscate: List[Term]
    engine: str = "pymupdf"
    
    def __post_init__(self):
        if not self.destination_path or not self.destination_path.strip():
            raise ValueError("Destination path cannot be empty")
        if not self.terms_to_obfuscate:
            raise ValueError("Must specify at least one term to obfuscate")
        if not self.engine or not self.engine.strip():
            raise ValueError("Engine cannot be empty")


@dataclass(frozen=True)
class ObfuscationResult:
    """Result of document obfuscation."""
    success: bool
    output_document: Optional[Document]
    term_results: List[TermResult]
    total_terms_processed: int
    total_occurrences_obfuscated: int
    message: str
    error: Optional[str] = None
    
    @property
    def has_errors(self) -> bool:
        """Whether any errors occurred during processing."""
        return not self.success or self.error is not None
    
    @property
    def successfully_processed_terms(self) -> List[TermResult]:
        """Terms that were successfully processed."""
        return [result for result in self.term_results if result.was_found] 