"""
FastAPI adapter for PDF obfuscation service.
"""
import tempfile
import os
from typing import List, Optional
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
    description="PDF document obfuscation service",
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
    Obfuscate a PDF document via JSON request (like the original API).
    
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
        engine=request.engine
    )
    # If error, return 500 with detail
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error or "Obfuscation failed")
    # Compose response with output_path
    response = _convert_result_to_response(result)
    response_dict = response.model_dump()
    response_dict["output_path"] = response_dict.get("output_document")
    if "output_path" not in response_dict:
        response_dict["output_path"] = None
    return response_dict


@app.post("/obfuscate-upload")
async def obfuscate_upload(
    file: UploadFile = File(...),
    terms: str = Form(...),
    engine: str = Form("pymupdf")
):
    """
    Obfuscate a PDF document via file upload (form-data).
    
    Args:
        file: Uploaded PDF file
        terms: Comma-separated list of terms to obfuscate
        engine: Obfuscation engine to use
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files can be uploaded")
    
    # Parse terms
    term_list = [term.strip() for term in terms.split(',') if term.strip()]
    if not term_list:
        raise HTTPException(status_code=400, detail="At least one term must be specified")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        content = await file.read()
        temp_file.write(content)
        temp_file_path = temp_file.name
    
    try:
        # Execute obfuscation
        result = pdf_app.obfuscate_document(
            source_path=temp_file_path,
            terms=term_list,
            engine=engine
        )
        
        # Return obfuscated file if successful
        if result.success and result.output_document:
            return FileResponse(
                result.output_document.path,
                media_type='application/pdf',
                filename=f"obfuscated_{file.filename}"
            )
        else:
            # Return JSON response with error details
            return _convert_result_to_response(result)
            
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file_path)
        except:
            pass


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

 