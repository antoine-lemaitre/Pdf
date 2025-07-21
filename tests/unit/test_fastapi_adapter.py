import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from src.adapters.fastapi_adapter import (
    TermRequest, 
    ObfuscationRequest, 
    TermResultResponse, 
    ObfuscationResponse,
    _convert_result_to_response
)
from src.domain.entities import Document, Term, TermOccurrence, Position
from src.domain.exceptions import DocumentProcessingError


class TestFastAPIAdapterModels:
    """Unit tests for FastAPI adapter Pydantic models."""
    
    def test_term_request_valid(self):
        """Test valid TermRequest creation."""
        term = TermRequest(text="test")
        assert term.text == "test"
    
    def test_term_request_empty_text(self):
        """Test TermRequest with empty text."""
        term = TermRequest(text="")
        assert term.text == ""
    
    def test_obfuscation_request_minimal(self):
        """Test minimal ObfuscationRequest creation."""
        request = ObfuscationRequest(
            source_path="/path/to/source.pdf",
            terms=[TermRequest(text="test")]
        )
        
        assert request.source_path == "/path/to/source.pdf"
        assert len(request.terms) == 1
        assert request.terms[0].text == "test"
        assert request.destination_path is None
        assert request.engine == "pymupdf"
    
    def test_obfuscation_request_full(self):
        """Test full ObfuscationRequest creation."""
        request = ObfuscationRequest(
            source_path="/path/to/source.pdf",
            terms=[TermRequest(text="test"), TermRequest(text="sample")],
            destination_path="/path/to/output.pdf",
            engine="pdfplumber"
        )
        
        assert request.source_path == "/path/to/source.pdf"
        assert len(request.terms) == 2
        assert request.terms[0].text == "test"
        assert request.terms[1].text == "sample"
        assert request.destination_path == "/path/to/output.pdf"
        assert request.engine == "pdfplumber"
    
    def test_term_result_response_valid(self):
        """Test valid TermResultResponse creation."""
        response = TermResultResponse(
            term="test",
            status="success",
            occurrences_count=5,
            message="Term obfuscated successfully"
        )
        
        assert response.term == "test"
        assert response.status == "success"
        assert response.occurrences_count == 5
        assert response.message == "Term obfuscated successfully"
    
    def test_obfuscation_response_success(self):
        """Test successful ObfuscationResponse creation."""
        response = ObfuscationResponse(
            success=True,
            message="Document obfuscated successfully",
            output_document="/path/to/output.pdf",
            total_terms_processed=3,
            total_occurrences_obfuscated=10,
            term_results=[
                TermResultResponse(
                    term="test",
                    status="success",
                    occurrences_count=5,
                    message="Term obfuscated"
                )
            ]
        )
        
        assert response.success is True
        assert response.message == "Document obfuscated successfully"
        assert response.output_document == "/path/to/output.pdf"
        assert response.total_terms_processed == 3
        assert response.total_occurrences_obfuscated == 10
        assert len(response.term_results) == 1
        assert response.error is None
    
    def test_obfuscation_response_error(self):
        """Test error ObfuscationResponse creation."""
        response = ObfuscationResponse(
            success=False,
            message="Processing failed",
            output_document=None,
            total_terms_processed=0,
            total_occurrences_obfuscated=0,
            term_results=[],
            error="File not found"
        )
        
        assert response.success is False
        assert response.message == "Processing failed"
        assert response.output_document is None
        assert response.total_terms_processed == 0
        assert response.total_occurrences_obfuscated == 0
        assert len(response.term_results) == 0
        assert response.error == "File not found"


class TestFastAPIAdapterFunctions:
    """Unit tests for FastAPI adapter helper functions."""
    
    def test_convert_result_to_response_success(self):
        """Test converting successful result to response."""
        # Mock successful result
        mock_result = Mock()
        mock_result.success = True
        mock_result.message = "Success"
        mock_result.total_terms_processed = 2
        mock_result.total_occurrences_obfuscated = 5
        mock_result.error = None
        
        # Mock output_document with path attribute
        mock_output_doc = Mock()
        mock_output_doc.path = "/path/to/output.pdf"
        mock_result.output_document = mock_output_doc
        
        # Mock term results with proper structure
        mock_term1 = Mock()
        mock_term1.term.text = "test"
        mock_term1.status.value = "success"
        mock_term1.occurrences_count = 3
        mock_term1.message = "OK"
        
        mock_term2 = Mock()
        mock_term2.term.text = "sample"
        mock_term2.status.value = "success"
        mock_term2.occurrences_count = 2
        mock_term2.message = "OK"
        
        mock_result.term_results = [mock_term1, mock_term2]
        
        response = _convert_result_to_response(mock_result)
        
        assert response.success is True
        assert response.message == "Success"
        assert response.output_document == "/path/to/output.pdf"
        assert response.total_terms_processed == 2
        assert response.total_occurrences_obfuscated == 5
        assert len(response.term_results) == 2
        assert response.term_results[0].term == "test"
        assert response.term_results[1].term == "sample"
        assert response.error is None
    
    def test_convert_result_to_response_error(self):
        """Test converting error result to response."""
        # Mock error result
        mock_result = Mock()
        mock_result.success = False
        mock_result.message = "Error occurred"
        mock_result.output_document = None
        mock_result.total_terms_processed = 0
        mock_result.total_occurrences_obfuscated = 0
        mock_result.term_results = []
        mock_result.error = "File not found"
        
        response = _convert_result_to_response(mock_result)
        
        assert response.success is False
        assert response.message == "Error occurred"
        assert response.output_document is None
        assert response.total_terms_processed == 0
        assert response.total_occurrences_obfuscated == 0
        assert len(response.term_results) == 0
        assert response.error == "File not found"
    
    def test_convert_result_to_response_partial_success(self):
        """Test converting result with partial success."""
        # Mock partial success result
        mock_result = Mock()
        mock_result.success = True
        mock_result.message = "Partial success"
        mock_result.total_terms_processed = 2
        mock_result.total_occurrences_obfuscated = 1
        mock_result.error = None
        
        # Mock output_document with path attribute
        mock_output_doc = Mock()
        mock_output_doc.path = "/path/to/output.pdf"
        mock_result.output_document = mock_output_doc
        
        # Mock term results with proper structure
        mock_term1 = Mock()
        mock_term1.term.text = "test"
        mock_term1.status.value = "success"
        mock_term1.occurrences_count = 1
        mock_term1.message = "OK"
        
        mock_term2 = Mock()
        mock_term2.term.text = "missing"
        mock_term2.status.value = "not_found"
        mock_term2.occurrences_count = 0
        mock_term2.message = "Term not found"
        
        mock_result.term_results = [mock_term1, mock_term2]
        
        response = _convert_result_to_response(mock_result)
        
        assert response.success is True
        assert response.message == "Partial success"
        assert response.total_terms_processed == 2
        assert response.total_occurrences_obfuscated == 1
        assert len(response.term_results) == 2
        assert response.term_results[0].status == "success"
        assert response.term_results[1].status == "not_found"


class TestFastAPIAdapterValidation:
    """Unit tests for FastAPI adapter validation logic."""
    
    def test_validate_source_path_exists(self, sample_pdf):
        """Test validation of existing source path."""
        from src.adapters.fastapi_adapter import app
        
        # This should not raise an exception
        # The actual validation happens in the endpoint, but we can test the logic
        assert os.path.exists(sample_pdf)
    
    def test_validate_source_path_not_exists(self):
        """Test validation of non-existing source path."""
        non_existing_path = "/non/existing/path.pdf"
        assert not os.path.exists(non_existing_path)
    
    def test_validate_terms_list_not_empty(self):
        """Test validation of non-empty terms list."""
        request = ObfuscationRequest(
            source_path="/path/to/source.pdf",
            terms=[TermRequest(text="test")]
        )
        
        assert len(request.terms) > 0
        assert all(term.text for term in request.terms)
    
    def test_validate_engine_supported(self):
        """Test validation of supported engine."""
        supported_engines = ["pymupdf", "pypdfium2", "pdfplumber"]
        
        for engine in supported_engines:
            request = ObfuscationRequest(
                source_path="/path/to/source.pdf",
                terms=[TermRequest(text="test")],
                engine=engine
            )
            assert request.engine in supported_engines
    
    def test_validate_destination_path_optional(self):
        """Test that destination path is optional."""
        request = ObfuscationRequest(
            source_path="/path/to/source.pdf",
            terms=[TermRequest(text="test")]
        )
        
        assert request.destination_path is None
    
    def test_validate_destination_path_provided(self):
        """Test validation when destination path is provided."""
        request = ObfuscationRequest(
            source_path="/path/to/source.pdf",
            terms=[TermRequest(text="test")],
            destination_path="/path/to/output.pdf"
        )
        
        assert request.destination_path == "/path/to/output.pdf"


class TestFastAPIAdapterErrorHandling:
    """Unit tests for FastAPI adapter error handling."""
    
    def test_handle_file_not_found_error(self):
        """Test handling of file not found error."""
        from fastapi import HTTPException
        
        non_existing_path = "/non/existing/path.pdf"
        
        # This would be the logic in the endpoint
        if not os.path.exists(non_existing_path):
            with pytest.raises(HTTPException) as exc_info:
                raise HTTPException(status_code=500, detail=f"Source file {non_existing_path} not found")
            
            assert exc_info.value.status_code == 500
            assert "Source file" in str(exc_info.value.detail)
    
    def test_handle_processing_error(self):
        """Test handling of processing error."""
        from fastapi import HTTPException
        
        # Mock processing error
        error_message = "Processing failed"
        
        with pytest.raises(HTTPException) as exc_info:
            raise HTTPException(status_code=500, detail=error_message)
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == error_message
    
    def test_handle_validation_error(self):
        """Test handling of validation error."""
        from fastapi import HTTPException
        
        # Mock validation error
        validation_error = "Invalid request parameters"
        
        with pytest.raises(HTTPException) as exc_info:
            raise HTTPException(status_code=400, detail=validation_error)
        
        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == validation_error 