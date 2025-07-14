try:
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("PyMuPDF is required. Install with: pip install PyMuPDF")

from typing import List
from src.ports.pdf_processor_port import PdfProcessorPort
from src.domain.entities import Document, Term, TermOccurrence, Position
from src.domain.exceptions import DocumentProcessingError
from src.ports.file_storage_port import FileStoragePort


class PyMuPdfAdapter(PdfProcessorPort):
    """PyMuPDF adapter for PDF processing."""
    
    def __init__(self, file_storage: FileStoragePort):
        """Initialize the adapter with a storage system."""
        self.file_storage = file_storage
    
    def extract_text_occurrences(self, document: Document, term: Term) -> List[TermOccurrence]:
        """
        Extract all occurrences of a term in the document.
        
        Args:
            document: Document to analyze
            term: Term to search for
            
        Returns:
            List[TermOccurrence]: List of found occurrences
        """
        try:
            # Load document content
            document_content = self.file_storage.read_file(document.path)
            pdf_doc = fitz.open(stream=document_content, filetype="pdf")
            occurrences = []
            
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                
                # Case insensitive search - search for all variations
                variations = [term.text, term.text.lower(), term.text.upper(), term.text.capitalize()]
                text_instances = []
                for variation in variations:
                    instances = page.search_for(variation)
                    text_instances.extend(instances)
                
                # Remove duplicates based on coordinates
                seen = set()
                unique_instances = []
                for inst in text_instances:
                    inst_tuple = (inst.x0, inst.y0, inst.x1, inst.y1)
                    if inst_tuple not in seen:
                        seen.add(inst_tuple)
                        unique_instances.append(inst)
                text_instances = unique_instances
                
                for rect in text_instances:
                    position = Position(
                        x0=rect.x0,
                        y0=rect.y0,
                        x1=rect.x1,
                        y1=rect.y1
                    )
                    occurrence = TermOccurrence(
                        term=term,
                        position=position,
                        page_number=page_num + 1  # Pages numbered from 1
                    )
                    occurrences.append(occurrence)
            
            pdf_doc.close()
            return occurrences
            
        except Exception as e:
            raise DocumentProcessingError(f"Error during text extraction: {str(e)}")
    
    def obfuscate_occurrences(self, document: Document, occurrences: List[TermOccurrence]) -> bytes:
        """
        Obfuscate the document by masking occurrences with gray rectangles.
        Obfuscation is made permanent by flattening (image conversion).
        
        Args:
            document: Document to obfuscate
            occurrences: List of occurrences to mask
            
        Returns:
            bytes: Obfuscated and flattened PDF document (irreversible)
        """
        try:
            # Load document content
            document_content = self.file_storage.read_file(document.path)
            pdf_doc = fitz.open(stream=document_content, filetype="pdf")
            
            # Group occurrences by page
            occurrences_by_page = {}
            for occurrence in occurrences:
                page_num = occurrence.page_number - 1  # PyMuPDF uses 0-based index
                if page_num not in occurrences_by_page:
                    occurrences_by_page[page_num] = []
                occurrences_by_page[page_num].append(occurrence)
            
            # Add gray rectangles on each occurrence (NO BORDERS)
            for page_num, page_occurrences in occurrences_by_page.items():
                page = pdf_doc[page_num]
                
                for occurrence in page_occurrences:
                    rect = fitz.Rect(
                        occurrence.position.x0,
                        occurrence.position.y0,
                        occurrence.position.x1,
                        occurrence.position.y1
                    )
                    
                    # Add gray rectangle WITHOUT border to mask text
                    annot = page.add_rect_annot(rect)
                    annot.set_colors(stroke=[0.5, 0.5, 0.5], fill=[0.5, 0.5, 0.5])  # Uniform gray
                    annot.set_opacity(1.0)  # Opaque
                    annot.update()
            
            # CRITICAL STEP: Flattening to make obfuscation irreversible
            flattened_content = self._flatten_pdf_content(pdf_doc)
            pdf_doc.close()
            
            return flattened_content
            
        except Exception as e:
            raise DocumentProcessingError(f"Error during obfuscation: {str(e)}")
    
    def _flatten_pdf_content(self, doc: fitz.Document) -> bytes:
        """
        Flatten the PDF by converting each page to image then to PDF.
        This makes obfuscation permanent and irreversible.
        
        Args:
            doc: PyMuPDF document with annotations
            
        Returns:
            bytes: Flattened PDF
        """
        try:
            # Create new document for flattened result
            flattened_doc = fitz.open()
            
            # Convert each page to high quality image then to PDF
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Use 2x resolution to balance quality/size
                matrix = fitz.Matrix(2, 2)
                pixmap = page.get_pixmap(matrix=matrix)
                
                # Convert to high quality JPEG
                img_data = pixmap.tobytes("jpeg", jpg_quality=95)
                
                # Create new page with image
                img_rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
                new_page = flattened_doc.new_page(width=page.rect.width, height=page.rect.height)
                new_page.insert_image(img_rect, stream=img_data)
                
                pixmap = None  # Free memory
            
            # Generate content with compression
            flattened_content = flattened_doc.tobytes(deflate=True, garbage=4)
            flattened_doc.close()
            
            return flattened_content
            
        except Exception as e:
            raise DocumentProcessingError(f"Error during flattening: {str(e)}")
    
    def get_engine_info(self) -> dict:
        """
        Returns information about the PyMuPDF engine.
        
        Returns:
            dict: Engine information
        """
        try:
            import fitz
            return {
                "name": "pymupdf",
                "version": fitz.VersionBind,
                "description": "PyMuPDF - Fast and reliable engine for rectangle overlay obfuscation",
                "features": [
                    "Text extraction",
                    "Rectangle overlay obfuscation", 
                    "Multi-page support",
                    "High performance"
                ],
                "supported_formats": ["PDF"]
            }
        except ImportError:
            return {
                "name": "pymupdf",
                "version": "unknown",
                "description": "PyMuPDF - Not available",
                "features": [],
                "supported_formats": []
            } 