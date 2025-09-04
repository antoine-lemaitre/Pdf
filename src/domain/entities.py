"""
Domain entities for PDF obfuscation.
Pure business objects with no external dependencies.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel


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
class TextExtractionResult:
    """Result of text extraction from a PDF."""
    text: str
    page_count: int
    word_count: int
    pages: List[str]
    execution_time: float = 0.0


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


# API Models for FastAPI
class TermRequest(BaseModel):
    """Term in request."""
    text: str


class ObfuscationRequestAPI(BaseModel):
    """Obfuscation request via JSON."""
    source_path: str
    terms: List[TermRequest]
    destination_path: Optional[str] = None
    engine: str = "pymupdf"
    evaluate_quality: bool = False


class QualityMetricsResponse(BaseModel):
    """Quality metrics response."""
    completeness_score: float
    precision_score: float
    visual_integrity_score: float
    overall_score: float
    non_obfuscated_terms: List[str] = []
    false_positive_terms: List[str] = []
    precision_details: Optional[Dict[str, Any]] = None


class QualityEvaluationRequest(BaseModel):
    """Quality evaluation request."""
    original_document_path: str
    obfuscated_document_path: str
    terms: List[TermRequest]
    engine_used: str = "unknown"
    evaluator_type: str = "tesseract"


class QualityEvaluationResponse(BaseModel):
    """Quality evaluation response."""
    success: bool
    metrics: Optional[QualityMetricsResponse] = None
    error: Optional[str] = None


class TermResultResponse(BaseModel):
    """Term result response."""
    term: str
    status: str
    occurrences_count: int
    message: str


class ObfuscationResponse(BaseModel):
    """Obfuscation response."""
    success: bool
    message: str
    output_document: Optional[str] = None
    total_terms_processed: int = 0
    total_occurrences_obfuscated: int = 0
    term_results: List[TermResultResponse] = []
    error: Optional[str] = None 