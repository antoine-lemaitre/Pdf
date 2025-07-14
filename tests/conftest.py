import pytest
import tempfile
import os
from pathlib import Path
import fitz  # PyMuPDF
from src.domain.entities import Term, ObfuscationRequest
from src.adapters.pymupdf_adapter import PyMuPdfAdapter
from src.adapters.pypdfium2_adapter import PyPdfium2Adapter
from src.adapters.local_storage_adapter import LocalStorageAdapter


@pytest.fixture
def sample_terms():
    """Sample terms for testing."""
    return [
        Term(text="test"),
        Term(text="sample"),
        Term(text="document")
    ]


@pytest.fixture
def sample_pdf():
    """Create a sample PDF for testing."""
    # Create a temporary PDF file
    temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    temp_pdf.close()
    
    # Create a simple PDF with some text
    doc = fitz.open()
    page = doc.new_page()
    
    # Add some text to the page
    text = """This is a test document.
    It contains some sample text for testing purposes.
    We can use this document to test our obfuscation functionality.
    
    Contact: test@example.com
    Phone: 123-456-7890
    """
    
    page.insert_text((50, 50), text)
    doc.save(temp_pdf.name)
    doc.close()
    
    yield temp_pdf.name
    
    # Cleanup
    try:
        os.unlink(temp_pdf.name)
    except:
        pass


@pytest.fixture
def pymupdf_processor():
    """PyMuPDF processor for testing."""
    storage = LocalStorageAdapter()
    return PyMuPdfAdapter(storage)


@pytest.fixture
def pypdfium2_processor():
    """PyPDFium2 processor for testing."""
    storage = LocalStorageAdapter()
    return PyPdfium2Adapter(storage)


@pytest.fixture
def pdf_processor():
    """Default PDF processor for testing (PyMuPDF)."""
    storage = LocalStorageAdapter()
    return PyMuPdfAdapter(storage)


@pytest.fixture
def temp_output_path():
    """Temporary output path for testing."""
    temp_file = tempfile.NamedTemporaryFile(suffix='_obfuscated.pdf', delete=False)
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    try:
        os.unlink(temp_file.name)
    except:
        pass


@pytest.fixture
def obfuscation_request(sample_pdf, temp_output_path, sample_terms):
    """Sample obfuscation request for testing."""
    from src.domain.entities import Document
    
    return ObfuscationRequest(
        source_document=Document(path=sample_pdf),
        destination_path=temp_output_path,
        terms_to_obfuscate=sample_terms,
        engine="pymupdf"
    ) 