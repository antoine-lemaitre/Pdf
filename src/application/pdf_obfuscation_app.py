"""
Application service for PDF obfuscation.
Coordinates domain services, use cases, and infrastructure adapters.
"""
from typing import List, Optional

from src.domain.entities import ObfuscationRequest, ObfuscationResult, Document, Term
from src.domain.services import DocumentObfuscationService
from src.domain.exceptions import ObfuscationError, DocumentProcessingError, FileStorageError
from src.use_cases.obfuscate_document import ObfuscateDocumentUseCase
from src.ports.pdf_processor_port import PdfProcessorPort
from src.ports.file_storage_port import FileStoragePort
from src.adapters.pymupdf_adapter import PyMuPdfAdapter
from src.adapters.pypdfium2_adapter import PyPdfium2Adapter
from src.adapters.pdfplumber_adapter import PdfPlumberAdapter
from src.adapters.local_storage_adapter import LocalStorageAdapter


class PdfObfuscationApplication:
    """Main application service for PDF obfuscation."""
    
    def __init__(
        self,
        pdf_processor: Optional[PdfProcessorPort] = None,
        file_storage: Optional[FileStoragePort] = None,
        default_engine: str = "pymupdf"
    ):
        """
        Initialize the application with its dependencies.
        
        Args:
            pdf_processor: PDF processor (default: PyMuPdfAdapter)
            file_storage: Storage system (default: LocalStorageAdapter)
            default_engine: Default engine to use (pymupdf)
        """
        # Default configuration
        self._file_storage = file_storage or LocalStorageAdapter()
        self._default_engine = default_engine
        self._pdf_processor = pdf_processor or self._create_processor(default_engine)
        
        # Domain services
        self._obfuscation_service = DocumentObfuscationService()
        
        # Use cases
        self._obfuscate_use_case = ObfuscateDocumentUseCase(
            pdf_processor=self._pdf_processor,
            file_storage=self._file_storage,
            obfuscation_service=self._obfuscation_service
        )
    
    def _create_processor(self, engine: str) -> PdfProcessorPort:
        """
        Create a PDF processor based on the specified engine.
        
        Args:
            engine: Engine name (pymupdf, pypdfium2, pdfplumber)
            
        Returns:
            PdfProcessorPort: Configured processor
            
        Raises:
            ObfuscationError: If engine is not supported
        """
        if engine == "pymupdf":
            return PyMuPdfAdapter(self._file_storage)
        elif engine == "pypdfium2":
            return PyPdfium2Adapter(self._file_storage)
        elif engine == "pdfplumber":
            return PdfPlumberAdapter(self._file_storage)
        else:
            raise ObfuscationError(f"Engine {engine} not supported. Available engines: pymupdf, pypdfium2, pdfplumber")
    
    def obfuscate_document(
        self,
        source_path: str,
        terms: List[str],
        destination_path: Optional[str] = None,
        engine: str = "pymupdf"
    ) -> ObfuscationResult:
        """
        Obfuscate a PDF document with the specified terms.
        
        Args:
            source_path: Path to the source document
            terms: List of terms to obfuscate
            destination_path: Destination path (optional)
            engine: Obfuscation engine to use
            
        Returns:
            ObfuscationResult: Obfuscation result
        """
        try:
            # Input validation
            if not source_path or not source_path.strip():
                raise ObfuscationError("Source document path cannot be empty")
            
            if not terms:
                raise ObfuscationError("At least one term must be specified")
            
            if engine not in ["pymupdf", "pypdfium2", "pdfplumber"]:
                raise ObfuscationError(f"Engine {engine} not supported. Available engines: pymupdf, pypdfium2, pdfplumber")
            
            # Check that source file exists
            if not self._file_storage.file_exists(source_path):
                raise ObfuscationError(f"Source file {source_path} does not exist")
            
            # Create obfuscation request
            source_document = Document(path=source_path)
            if destination_path:
                dest_path = destination_path
            else:
                import os
                base = os.path.basename(source_path)
                name, ext = os.path.splitext(base)
                dest_path = os.path.join("data/output", f"{name}_obfuscated{ext}")
            term_objects = [Term(text=term.strip()) for term in terms if term.strip()]
            
            request = ObfuscationRequest(
                source_document=source_document,
                destination_path=dest_path,
                terms_to_obfuscate=term_objects,
                engine=engine
            )
            
            # Validate request according to business rules
            self._obfuscation_service.validate_obfuscation_request(request)
            
            # Create processor for the specified engine
            processor = self._create_processor(engine)
            
            # Create use case with the correct processor
            use_case = ObfuscateDocumentUseCase(
                pdf_processor=processor,
                file_storage=self._file_storage,
                obfuscation_service=self._obfuscation_service
            )
            
            # Execute use case
            result = use_case.execute(source_path, [term.text for term in term_objects], dest_path)
            
            return result
            
        except (ObfuscationError, DocumentProcessingError, FileStorageError) as e:
            # Known business errors
            return self._obfuscation_service.create_error_result(
                error=str(e),
                engine=engine
            )
        except Exception as e:
            # Unexpected errors
            return self._obfuscation_service.create_error_result(
                error=f"Unexpected error: {str(e)}",
                engine=engine
            )
    
    def get_supported_engines(self) -> List[str]:
        """
        Returns the list of supported obfuscation engines.
        
        Returns:
            List[str]: List of supported engines
        """
        return ["pymupdf", "pypdfium2", "pdfplumber"]
    
    def validate_document(self, document_path: str) -> bool:
        """
        Validates that a document can be processed.
        
        Args:
            document_path: Path to the document
            
        Returns:
            bool: True if the document is valid
        """
        try:
            if not self._file_storage.file_exists(document_path):
                return False
                
            if not document_path.lower().endswith('.pdf'):
                return False
                
            # Try to open the document with the processor
            document = Document(path=document_path)
            # Basic test - try to extract text
            test_term = Term(text="test")
            self._pdf_processor.extract_text_occurrences(document, test_term)
            
            return True
            
        except Exception:
            return False 