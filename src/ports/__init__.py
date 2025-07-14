"""
Ports package - interfaces for external systems.
These define the contracts that adapters must implement.
"""

from .pdf_processor_port import PdfProcessorPort
from .file_storage_port import FileStoragePort

__all__ = [
    "PdfProcessorPort",
    "FileStoragePort",
] 