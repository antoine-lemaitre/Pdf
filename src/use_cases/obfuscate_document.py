from typing import List, Optional
from src.domain.entities import Document, Term, ObfuscationResult
from src.domain.services import DocumentObfuscationService
from src.ports.pdf_processor_port import PdfProcessorPort
from src.ports.file_storage_port import FileStoragePort
from src.domain.exceptions import DocumentProcessingError


class ObfuscateDocumentUseCase:
    """Use case for obfuscating a document with a list of terms."""
    
    def __init__(
        self,
        pdf_processor: PdfProcessorPort,
        file_storage: FileStoragePort,
        obfuscation_service: DocumentObfuscationService
    ):
        self._pdf_processor = pdf_processor
        self._file_storage = file_storage
        self._obfuscation_service = obfuscation_service
    
    def execute(self, document_path: str, terms: List[str], destination_path: Optional[str] = None) -> ObfuscationResult:
        """
        Execute document obfuscation.
        
        Args:
            document_path: Path to the PDF document
            terms: List of terms to obfuscate
            destination_path: Optional destination path for the obfuscated document
            
        Returns:
            ObfuscationResult: Obfuscation result
            
        Raises:
            DocumentProcessingError: In case of processing error
        """
        try:
            # Create document
            document = Document(path=document_path)
            
            # Create Term objects
            term_objects = [Term(text=term) for term in terms]
            
            # Extract occurrences for all terms
            all_occurrences = []
            for term in term_objects:
                occurrences = self._pdf_processor.extract_text_occurrences(document, term)
                all_occurrences.extend(occurrences)
            
            # Create results by term
            term_results = self._obfuscation_service.create_term_results(term_objects, all_occurrences)
            
            if all_occurrences:
                # Obfuscate document
                obfuscated_content = self._pdf_processor.obfuscate_occurrences(document, all_occurrences)
                
                # Save obfuscated document
                if destination_path:
                    output_path = destination_path
                else:
                    # Default to data/output/ if no destination specified
                    if 'data/input/' in document_path:
                        output_path = document_path.replace('data/input/', 'data/output/').replace('.pdf', '_obfuscated.pdf')
                    else:
                        output_path = document_path.replace('.pdf', '_obfuscated.pdf')
                self._file_storage.write_file(output_path, obfuscated_content)
                output_document = Document(path=output_path)
                
                # Create success result
                result = self._obfuscation_service.create_success_result(
                    output_document=output_document,
                    term_results=term_results,
                    engine=self._get_engine_name()
                )
            else:
                # No occurrences found
                result = self._obfuscation_service.create_error_result(
                    error="No terms found in the document",
                    term_results=term_results,
                    engine=self._get_engine_name()
                )
            
            return result
            
        except Exception as e:
            raise DocumentProcessingError(f"Error during document obfuscation {document_path}: {str(e)}")
    
    def _get_engine_name(self) -> str:
        """
        Get the name of the current PDF processor engine.
        
        Returns:
            str: Engine name
        """
        engine_info = self._pdf_processor.get_engine_info()
        return engine_info.get("name", "unknown") 