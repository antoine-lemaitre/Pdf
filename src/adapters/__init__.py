"""
PDF processing adapters module.
Provides various implementations for PDF text extraction and obfuscation.
"""

from .pymupdf_adapter import PyMuPdfAdapter
from .pypdfium2_adapter import PyPdfium2Adapter
from .pdfplumber_adapter import PdfPlumberAdapter

__all__ = [
    "PyMuPdfAdapter",
    "PyPdfium2Adapter", 
    "PdfPlumberAdapter"
] 