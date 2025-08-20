"""
FastAPI adapter for PDF obfuscation service.
"""
import tempfile
import os
from typing import List, Optional, Dict, Any
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException, UploadFile, File, Form
    from fastapi.responses import FileResponse, JSONResponse
    from pydantic import BaseModel
except ImportError:
    raise ImportError("FastAPI is required. Install with: pip install fastapi python-multipart")

from src.application.pdf_obfuscation_app import PdfObfuscationApplication


# Pydantic models for API
class TermRequest(BaseModel):
    """Term in request."""
    text: str


class ObfuscationRequest(BaseModel):
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


class QualityEvaluationResponse(BaseModel):
    """Quality evaluation response."""
    original_document_path: str
    obfuscated_document_path: str
    terms_to_obfuscate: List[str]
    engine_used: str
    metrics: QualityMetricsResponse
    timestamp: str


class TermResultResponse(BaseModel):
    """Result for a specific term."""
    term: str
    status: str
    occurrences_count: int
    message: str


class ObfuscationResponse(BaseModel):
    """Obfuscation response."""
    success: bool
    message: str
    output_document: Optional[str]
    total_terms_processed: int
    total_occurrences_obfuscated: int
    term_results: List[TermResultResponse]
    error: Optional[str] = None


# FastAPI application configuration
app = FastAPI(
    title="PDF Obfuscation Service",
    description="PDF document obfuscation service with quality evaluation",
    version="1.0.0"
)

# Global application instance
pdf_app = PdfObfuscationApplication()


@app.get("/health")
async def health_check():
    """Service health check."""
    return {"status": "healthy", "service": "pdf-obfuscator"}


@app.get("/engines")
async def get_engines():
    """Get available obfuscation engines."""
    engines = pdf_app.get_supported_engines()
    return {
        "available_engines": [{"name": e} for e in engines],
        "count": len(engines)
    }


@app.post("/obfuscate", response_model=ObfuscationResponse)
async def obfuscate_document(request: ObfuscationRequest):
    """
    Obfuscate a PDF document via JSON request.
    
    Args:
        request: Obfuscation request
    """
    # Validate source file
    if not os.path.exists(request.source_path):
        raise HTTPException(status_code=500, detail=f"Source file {request.source_path} not found")
    
    # Convert terms to list of strings
    terms = [term.text for term in request.terms]
    
    # Execute obfuscation
    result = pdf_app.obfuscate_document(
        source_path=request.source_path,
        terms=terms,
        destination_path=request.destination_path,
        engine=request.engine,
        evaluate_quality=request.evaluate_quality
    )
    
    return _convert_result_to_response(result)


@app.post("/evaluate-quality", response_model=QualityEvaluationResponse)
async def evaluate_quality(request: QualityEvaluationRequest):
    """
    Evaluate the quality of obfuscation.
    
    Args:
        request: Quality evaluation request
    """
    # Validate files exist
    if not os.path.exists(request.original_document_path):
        raise HTTPException(
            status_code=400, 
            detail=f"Original document {request.original_document_path} not found"
        )
    
    if not os.path.exists(request.obfuscated_document_path):
        raise HTTPException(
            status_code=400, 
            detail=f"Obfuscated document {request.obfuscated_document_path} not found"
        )
    
    # Convert terms to list of strings
    terms = [term.text for term in request.terms]
    
    # Execute quality evaluation
    quality_report = pdf_app.evaluate_quality(
        original_document_path=request.original_document_path,
        obfuscated_document_path=request.obfuscated_document_path,
        terms_to_obfuscate=terms,
        engine_used=request.engine_used
    )
    
    # Extract precision details from the quality report
    precision_details = None
    if hasattr(quality_report.metrics, 'details') and 'precision' in quality_report.metrics.details:
        precision_details = quality_report.metrics.details['precision']
    
    return QualityEvaluationResponse(
        original_document_path=quality_report.original_document_path,
        obfuscated_document_path=quality_report.obfuscated_document_path,
        terms_to_obfuscate=quality_report.terms_to_obfuscate,
        engine_used=quality_report.engine_used,
        metrics=QualityMetricsResponse(
            completeness_score=quality_report.metrics.completeness_score,
            precision_score=quality_report.metrics.precision_score,
            visual_integrity_score=quality_report.metrics.visual_integrity_score,
            overall_score=quality_report.metrics.overall_score,
            non_obfuscated_terms=quality_report.metrics.non_obfuscated_terms,
            false_positive_terms=quality_report.metrics.false_positive_terms,
            precision_details=precision_details
        ),
        timestamp=quality_report.timestamp
    )





def _convert_result_to_response(result) -> ObfuscationResponse:
    """Convert an ObfuscationResult to ObfuscationResponse."""
    term_results = [
        TermResultResponse(
            term=tr.term.text,
            status=tr.status.value,
            occurrences_count=tr.occurrences_count,
            message=tr.message
        )
        for tr in result.term_results
    ]
    
    return ObfuscationResponse(
        success=result.success,
        message=result.message,
        output_document=result.output_document.path if result.output_document else None,
        total_terms_processed=result.total_terms_processed,
        total_occurrences_obfuscated=result.total_occurrences_obfuscated,
        term_results=term_results,
        error=result.error
    )


def create_app():
    """Create and configure the FastAPI application."""
    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

 