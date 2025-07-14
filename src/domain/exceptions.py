"""
Domain exceptions for PDF obfuscation.
Business-specific errors that can occur in the domain layer.
"""


class DomainError(Exception):
    """Base exception for all domain errors."""
    pass


class DocumentNotFoundError(DomainError):
    """Raised when a document file cannot be found."""
    pass


class DocumentProcessingError(DomainError):
    """Raised when there's an error processing a document."""
    pass


class OutputWriteError(DomainError):
    """Raised when there's an error writing the output file."""
    pass


class FileReadError(DomainError):
    """Raised when there's an error reading a file."""
    pass


class FileWriteError(DomainError):
    """Raised when there's an error writing a file."""
    pass


class FileCopyError(DomainError):
    """Raised when there's an error copying a file."""
    pass


class FileDeleteError(DomainError):
    """Raised when there's an error deleting a file."""
    pass


class InvalidEngineError(DomainError):
    """Raised when an invalid engine is specified."""
    pass


class ObfuscationError(DomainError):
    """Raised when there's a general obfuscation error."""
    pass


class FileStorageError(DomainError):
    """Raised when there's an error with file storage operations."""
    pass 