import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from src.adapters.fastapi_adapter import app


class TestFastAPI:
    """Integration tests for FastAPI endpoints."""
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "pdf-obfuscator"
    
    def test_engines_endpoint(self):
        """Test engines listing endpoint."""
        client = TestClient(app)
        response = client.get("/engines")
        
        assert response.status_code == 200
        data = response.json()
        assert "available_engines" in data
        engines = data["available_engines"]
        assert len(engines) == 3  # We have three engines: pymupdf, pypdfium2, and pdfplumber
        
        # Check all engines are present
        engine_names = [e["name"] for e in engines]
        assert "pymupdf" in engine_names
        assert "pypdfium2" in engine_names
        assert "pdfplumber" in engine_names
    
    def test_obfuscate_endpoint_missing_file(self, temp_output_path):
        """Test obfuscation endpoint with missing source file."""
        client = TestClient(app)
        
        request_data = {
            "source_path": "/nonexistent/file.pdf",
            "destination_path": temp_output_path,
            "terms": [{"text": "test"}],
            "engine": "pymupdf"
        }
        
        response = client.post("/obfuscate", json=request_data)
        assert response.status_code == 500  # Internal server error (handled as 500)
    
    def test_obfuscate_endpoint_pymupdf(self, sample_pdf, temp_output_path):
        """Test JSON obfuscation endpoint with PyMuPDF."""
        client = TestClient(app)
        
        request_data = {
            "source_path": sample_pdf,
            "destination_path": temp_output_path,
            "terms": [
                {"text": "test"},
                {"text": "document"}
            ],
            "engine": "pymupdf"
        }
        
        response = client.post("/obfuscate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["output_document"] == temp_output_path
        assert data["total_terms_processed"] == 2
        assert len(data["term_results"]) == 2
        assert "Obfuscation completed successfully" in data["message"]
    
    def test_obfuscate_endpoint_pypdfium2(self, sample_pdf, temp_output_path):
        """Test JSON obfuscation endpoint with PyPDFium2."""
        client = TestClient(app)
        
        request_data = {
            "source_path": sample_pdf,
            "destination_path": temp_output_path,
            "terms": [
                {"text": "test"},
                {"text": "document"}
            ],
            "engine": "pypdfium2"
        }
        
        response = client.post("/obfuscate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["output_document"] == temp_output_path
        assert data["total_terms_processed"] == 2
        assert len(data["term_results"]) == 2
        assert "Obfuscation completed successfully" in data["message"]
    
    def test_obfuscate_endpoint_invalid_engine(self, sample_pdf, temp_output_path):
        """Test obfuscation endpoint with invalid engine."""
        client = TestClient(app)
        
        request_data = {
            "source_path": sample_pdf,
            "destination_path": temp_output_path,
            "terms": [{"text": "test"}],
            "engine": "invalid_engine"
        }
        
        response = client.post("/obfuscate", json=request_data)
        assert response.status_code == 500  # Internal server error (validation error handled as 500)
        
        data = response.json()
        assert "invalid_engine" in data["detail"]
        assert "Available engines" in data["detail"]


@pytest.mark.asyncio
class TestAsyncFastAPI:
    """Async integration tests for FastAPI."""
    
    async def test_health_async(self):
        """Test health endpoint asynchronously."""
        from fastapi.testclient import TestClient
        # Use synchronous client for simplicity
        client = TestClient(app)
        response = client.get("/health")
            
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    async def test_engines_async(self):
        """Test engines endpoint asynchronously."""
        from fastapi.testclient import TestClient
        # Use synchronous client for simplicity
        client = TestClient(app)
        response = client.get("/engines")
            
        assert response.status_code == 200
        data = response.json()
        assert "available_engines" in data 