"""
Error handler service for PDF obfuscation.
Centralizes error handling and provides consistent error responses.
"""
from typing import Dict, Any, Optional, Type
from ..entities import ObfuscationResult, QualityReport
from ..exceptions import (
    ObfuscationError, 
    DocumentProcessingError, 
    FileStorageError,
    ValidationError
)
from ..services import DocumentObfuscationService


class ErrorContext:
    """Context information for error handling."""
    
    def __init__(self, operation: str, **kwargs):
        """
        Initialize error context.
        
        Args:
            operation: Operation being performed
            **kwargs: Additional context information
        """
        self.operation = operation
        self.context = kwargs
    
    def add_context(self, **kwargs):
        """Add additional context information."""
        self.context.update(kwargs)
    
    def get_context(self) -> Dict[str, Any]:
        """Get all context information."""
        return {
            "operation": self.operation,
            **self.context
        }


class ErrorHandler:
    """Centralized error handler for the application."""
    
    def __init__(self, obfuscation_service: DocumentObfuscationService):
        """
        Initialize error handler.
        
        Args:
            obfuscation_service: Service for creating error results
        """
        self._obfuscation_service = obfuscation_service
        self._error_mapping = self._create_error_mapping()
    
    def handle_obfuscation_error(
        self, 
        error: Exception, 
        context: ErrorContext,
        engine: str = "unknown"
    ) -> ObfuscationResult:
        """
        Handle errors during obfuscation operations.
        
        Args:
            error: The error that occurred
            context: Context information about the operation
            engine: Engine being used
            
        Returns:
            Error result with appropriate error information
        """
        error_info = self._analyze_error(error, context)
        
        # Create appropriate error result
        if isinstance(error, ObfuscationError):
            return self._obfuscation_service.create_error_result(
                error=error_info["message"],
                engine=engine
            )
        elif isinstance(error, DocumentProcessingError):
            return self._obfuscation_service.create_error_result(
                error=f"Document processing error: {error_info['message']}",
                engine=engine
            )
        elif isinstance(error, FileStorageError):
            return self._obfuscation_service.create_error_result(
                error=f"File storage error: {error_info['message']}",
                engine=engine
            )
        elif isinstance(error, ValidationError):
            return self._obfuscation_service.create_error_result(
                error=f"Validation error: {error_info['message']}",
                engine=engine
            )
        else:
            # Unexpected error
            return self._obfuscation_service.create_error_result(
                error=f"Unexpected error during {context.operation}: {error_info['message']}",
                engine=engine
            )
    
    def handle_quality_evaluation_error(
        self, 
        error: Exception, 
        context: ErrorContext
    ) -> QualityReport:
        """
        Handle errors during quality evaluation.
        
        Args:
            error: The error that occurred
            context: Context information about the operation
            
        Returns:
            Default quality report with error information
        """
        error_info = self._analyze_error(error, context)
        
        # Create a default quality report indicating failure
        from ..entities import QualityMetrics
        from datetime import datetime
        
        error_metrics = QualityMetrics(
            completeness_score=0.0,
            precision_score=0.0,
            visual_integrity_score=0.0,
            overall_score=0.0,
            details={
                "error": error_info["message"],
                "error_type": error_info["type"],
                "context": context.get_context()
            },
            non_obfuscated_terms=[],
            false_positive_terms=[]
        )
        
        return QualityReport(
            original_document_path=context.context.get("original_path", "unknown"),
            obfuscated_document_path=context.context.get("obfuscated_path", "unknown"),
            terms_to_obfuscate=context.context.get("terms", []),
            engine_used=context.context.get("engine", "unknown"),
            metrics=error_metrics,
            timestamp=datetime.now().isoformat()
        )
    
    def handle_validation_error(
        self, 
        error: Exception, 
        context: ErrorContext
    ) -> bool:
        """
        Handle errors during validation operations.
        
        Args:
            error: The error that occurred
            context: Context information about the operation
            
        Returns:
            False to indicate validation failure
        """
        # For validation errors, we return False to indicate failure
        # The error details are logged but not returned
        error_info = self._analyze_error(error, context)
        return False
    
    def _analyze_error(self, error: Exception, context: ErrorContext) -> Dict[str, Any]:
        """
        Analyze an error and extract relevant information.
        
        Args:
            error: The error to analyze
            context: Context information
            
        Returns:
            Dictionary with error analysis
        """
        error_type = type(error).__name__
        error_message = str(error)
        
        # Add context information to error message
        context_info = context.get_context()
        
        return {
            "type": error_type,
            "message": error_message,
            "context": context_info,
            "timestamp": self._get_timestamp()
        }
    
    def _create_error_mapping(self) -> Dict[Type[Exception], Dict[str, Any]]:
        """Create mapping of error types to handling strategies."""
        return {
            ObfuscationError: {
                "category": "business_logic",
                "severity": "high",
                "recoverable": False
            },
            DocumentProcessingError: {
                "category": "processing",
                "severity": "medium",
                "recoverable": True
            },
            FileStorageError: {
                "category": "infrastructure",
                "severity": "medium",
                "recoverable": True
            },
            ValidationError: {
                "category": "input_validation",
                "severity": "low",
                "recoverable": True
            }
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for error logging."""
        from datetime import datetime
        return datetime.now().isoformat()
