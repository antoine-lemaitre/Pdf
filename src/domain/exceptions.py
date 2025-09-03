"""
Domain exceptions for PDF obfuscation.
"""


class ObfuscationError(Exception):
    """Base exception for obfuscation errors."""
    pass


class DocumentProcessingError(Exception):
    """Exception raised when document processing fails."""
    pass


class FileStorageError(Exception):
    """Exception raised when file storage operations fail."""
    pass


class ValidationError(Exception):
    """Exception raised when validation fails."""
    pass 