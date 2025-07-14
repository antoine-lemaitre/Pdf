import pytest
import tempfile
import os
from src.adapters.pymupdf_adapter import PyMuPdfAdapter
from src.adapters.local_storage_adapter import LocalStorageAdapter
from src.domain.entities import Document, Term


class TestPyMuPdfAdapter:
    """Unit tests for PyMuPdfAdapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create PyMuPdfAdapter instance."""
        storage = LocalStorageAdapter()
        return PyMuPdfAdapter(storage)
    
    def test_extract_text_occurrences(self, adapter, sample_pdf):
        """Test text extraction."""
        document = Document(path=sample_pdf)
        term = Term(text="test")
        
        occurrences = adapter.extract_text_occurrences(document, term)
        
        assert len(occurrences) > 0
        assert all(occ.term.text == "test" for occ in occurrences)
        assert all(occ.page_number == 1 for occ in occurrences)
    
    def test_obfuscate_occurrences(self, adapter, sample_pdf, temp_output_path):
        """Test obfuscation."""
        document = Document(path=sample_pdf)
        term = Term(text="test")
        
        # Extract occurrences first
        occurrences = adapter.extract_text_occurrences(document, term)
        assert len(occurrences) > 0
        
        # Obfuscate
        obfuscated_content = adapter.obfuscate_occurrences(document, occurrences)
        
        # Save and verify
        with open(temp_output_path, 'wb') as f:
            f.write(obfuscated_content)
        
        assert os.path.exists(temp_output_path)
        assert os.path.getsize(temp_output_path) > 0
    
    def test_get_engine_info(self, adapter):
        """Test engine info."""
        info = adapter.get_engine_info()
        
        assert info["name"] == "pymupdf"
        assert "version" in info
        assert "description" in info
        assert "features" in info
        assert "supported_formats" in info 