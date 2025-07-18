"""
This adapter uses pdfplumber for text extraction and pdf2image + Pillow for obfuscation.
Robust approach combining precise text extraction with raster-based obfuscation.
"""
import io
import tempfile
import os
from typing import List

try:
    import pdfplumber
    from PIL import Image, ImageDraw, ImageFilter
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import black
    from pdf2image import convert_from_bytes
except ImportError:
    raise ImportError("pdfplumber, pdf2image, Pillow, and reportlab are required. Install with: pip install pdfplumber pdf2image Pillow reportlab")

from src.ports.pdf_processor_port import PdfProcessorPort
from src.domain.entities import Document, Term, TermOccurrence, Position
from src.domain.exceptions import DocumentProcessingError
from src.ports.file_storage_port import FileStoragePort


class PdfPlumberAdapter(PdfProcessorPort):
    """
    PdfPlumber adapter for PDF processing with pdf2image + Pillow obfuscation.
    Combines precise text extraction with robust raster-based obfuscation.
    """
    
    def __init__(self, file_storage: FileStoragePort):
        """Initialize the adapter with a storage system."""
        self.file_storage = file_storage
    
    def extract_text_occurrences(self, document: Document, term: Term) -> List[TermOccurrence]:
        """
        Extract all occurrences of a term using pdfplumber's precise text extraction.
        
        Args:
            document: Document to analyze
            term: Term to search for
            
        Returns:
            List[TermOccurrence]: List of found occurrences
        """
        try:
            # Load document content
            document_content = self.file_storage.read_file(document.path)
            occurrences = []
            
            # Open PDF with pdfplumber
            with pdfplumber.open(io.BytesIO(document_content)) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Extract words with positioning information
                    words = page.extract_words()
                    
                    print(f"DEBUG: Page {page_num + 1} words extracted by pdfplumber:")
                    print(f"DEBUG: Found {len(words)} words")
                    
                    # Split term into individual words
                    term_words = term.text.split()
                    print(f"DEBUG: Looking for term words: {term_words}")
                    
                    # Search for consecutive words that match our term
                    for i in range(len(words) - len(term_words) + 1):
                        # Check if the next words match our term
                        match = True
                        for j, term_word in enumerate(term_words):
                            if i + j >= len(words) or words[i + j]['text'].lower() != term_word.lower():
                                match = False
                                break
                        
                        if match:
                            # Found consecutive words that match our term
                            print(f"DEBUG: Found term at word index {i}")
                            
                            # Calculate bounding box from all matching words
                            matching_words = words[i:i + len(term_words)]
                            x0 = min(word['x0'] for word in matching_words)
                            y0 = min(word['top'] for word in matching_words)
                            x1 = max(word['x1'] for word in matching_words)
                            y1 = max(word['bottom'] for word in matching_words)
                            
                            position = Position(x0=x0, y0=y0, x1=x1, y1=y1)
                            
                            occurrence = TermOccurrence(
                                term=term,
                                position=position,
                                page_number=page_num + 1
                            )
                            occurrences.append(occurrence)
            
            return occurrences
            
        except Exception as e:
            raise DocumentProcessingError(f"Error during text extraction with pdfplumber: {str(e)}")
    

    
    def obfuscate_occurrences(self, document: Document, occurrences: List[TermOccurrence]) -> bytes:
        """
        Obfuscate using pdf2image + Pillow with corrected coordinate mapping.
        Uses precise coordinate conversion from pdfplumber to image coordinates.
        
        Args:
            document: Document to obfuscate
            occurrences: List of occurrences to obfuscate
            
        Returns:
            bytes: Obfuscated PDF document
        """
        try:
            # Load document content
            document_content = self.file_storage.read_file(document.path)
            
            # Group occurrences by page
            occurrences_by_page = {}
            for occurrence in occurrences:
                page_num = occurrence.page_number - 1  # 0-based index
                if page_num not in occurrences_by_page:
                    occurrences_by_page[page_num] = []
                occurrences_by_page[page_num].append(occurrence)
            
            # Convert PDF to images using pdf2image
            images = convert_from_bytes(
                document_content,
                dpi=200,  # High resolution for better quality
                fmt='PNG'
            )
            
            # Get page information from pdfplumber for accurate coordinate conversion
            page_info_list = []
            with pdfplumber.open(io.BytesIO(document_content)) as pdf:
                for page in pdf.pages:
                    page_info_list.append({
                        'width': page.width,
                        'height': page.height,
                        'bbox': page.bbox
                    })
            
            # Process each page
            processed_images = []
            for page_num, image in enumerate(images):
                if page_num in occurrences_by_page:
                    # Apply obfuscation to this page
                    page_info = page_info_list[page_num] if page_num < len(page_info_list) else None
                    processed_image = self._apply_obfuscation_to_image(
                        image, 
                        occurrences_by_page[page_num],
                        page_info
                    )
                else:
                    processed_image = image
                
                processed_images.append(processed_image)
            
            # Convert back to PDF using ReportLab
            return self._images_to_pdf(processed_images)
            
        except Exception as e:
            raise DocumentProcessingError(f"Error during obfuscation: {str(e)}")
    
    def _apply_obfuscation_to_image(self, image: Image.Image, occurrences: List[TermOccurrence], page_info: dict | None = None) -> Image.Image:
        """
        Apply obfuscation to a single image page with corrected coordinate mapping.
        
        Args:
            image: PIL Image to process
            occurrences: List of occurrences on this page
            page_info: Page information from pdfplumber for accurate coordinate conversion
            
        Returns:
            Image.Image: Processed image
        """
        # Create a copy to avoid modifying original
        processed_image = image.copy()
        draw = ImageDraw.Draw(processed_image)
        
        img_width, img_height = image.size
        
        print(f"DEBUG: Image size: {img_width}x{img_height}")
        
        for occurrence in occurrences:
            # Get page dimensions from pdfplumber
            if page_info:
                page_width_pt = page_info['width']
                page_height_pt = page_info['height']
                page_bbox = page_info['bbox']
            else:
                # Fallback to A4 dimensions
                page_width_pt = 595.5
                page_height_pt = 842.25
                page_bbox = (0, 0, page_width_pt, page_height_pt)
            
            # Extract bbox coordinates
            bbox_x0, bbox_y0, bbox_x1, bbox_y1 = page_bbox
            
            print(f"DEBUG: Page dimensions: {page_width_pt}x{page_height_pt}")
            print(f"DEBUG: Page bbox: {page_bbox}")
            print(f"DEBUG: Bbox coordinates: x0={bbox_x0}, y0={bbox_y0}, x1={bbox_x1}, y1={bbox_y1}")
            print(f"DEBUG: Term '{occurrence.term.text}' - pdfplumber coords: x0={occurrence.position.x0}, y0={occurrence.position.y0}, x1={occurrence.position.x1}, y1={occurrence.position.y1}")
            print(f"DEBUG: Term size: {occurrence.position.x1 - occurrence.position.x0} x {occurrence.position.y1 - occurrence.position.y0} points")
            print(f"DEBUG: Term found: '{occurrence.term.text}'")
            print(f"DEBUG: Term searched: '{occurrence.term.text}'")
            
            # Calculate scale factors based on actual dimensions
            # Page PDF: 595.5 x 842.25 points
            # Image: 1655 x 2340 pixels
            scale_x = img_width / page_width_pt
            scale_y = img_height / page_height_pt
            
            # Convert pdfplumber coordinates to image coordinates
            # pdfplumber uses (x0, y0, x1, y1) where y0 is bottom, y1 is top
            # image uses (x, y) where y=0 is top
            
            # Scale X coordinates and adjust for bbox offset
            x0 = int((occurrence.position.x0 - bbox_x0) * scale_x)
            x1 = int((occurrence.position.x1 - bbox_x0) * scale_x)
            
            # Convert Y coordinates: pdfplumber bottom-left to image top-left
            # pdfplumber y0 is bottom, y1 is top
            # image y=0 is top
            y0_pdf = occurrence.position.y0  # bottom in pdfplumber
            y1_pdf = occurrence.position.y1  # top in pdfplumber
            
            # Convert to image coordinates - WITH BBOX OFFSET BUT NO INVERSION
            # Adjust for the negative bbox_y0 offset, but don't invert Y
            y0_adjusted = y0_pdf - bbox_y0  # Adjust for negative bbox_y0
            y1_adjusted = y1_pdf - bbox_y0  # Adjust for negative bbox_y0
            
            # Scale without inversion
            y0_img = int(y0_adjusted * scale_y)
            y1_img = int(y1_adjusted * scale_y)
            
            # Ensure coordinates are in correct order
            x0, x1 = min(x0, x1), max(x0, x1)
            y0_img, y1_img = min(y0_img, y1_img), max(y0_img, y1_img)
            
            print(f"DEBUG: Converted coords: x0={x0}, y0={y0_img}, x1={x1}, y1={y1_img}")
            print(f"DEBUG: Rectangle size: {x1-x0}x{y1_img-y0_img}")
            print(f"DEBUG: Bbox adjustment: x0-{bbox_x0}={occurrence.position.x0}-{bbox_x0}={occurrence.position.x0-bbox_x0}")
            print(f"DEBUG: Bbox adjustment: y1-{bbox_y1}={bbox_y1}-{occurrence.position.y1}={bbox_y1-occurrence.position.y1}")
            
            # Apply obfuscation
            draw.rectangle([x0, y0_img, x1, y1_img], fill=(0, 0, 0))
        
        return processed_image
    
    def _images_to_pdf(self, images: List[Image.Image]) -> bytes:
        """
        Convert list of PIL images back to PDF using ReportLab.
        
        Args:
            images: List of PIL Images
            
        Returns:
            bytes: PDF content
        """
        output_buffer = io.BytesIO()
        c = canvas.Canvas(output_buffer)
        
        for i, image in enumerate(images):
            # Get image dimensions
            img_width, img_height = image.size
            
            # Convert to PDF page size (A4)
            page_width = 595
            page_height = 842
            
            # Save image to buffer
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            # Add to PDF
            c.setPageSize((page_width, page_height))
            c.drawImage(ImageReader(img_buffer), 0, 0, page_width, page_height)
            
            # Add page break if not the last page
            if i < len(images) - 1:
                c.showPage()
        
        c.save()
        return output_buffer.getvalue()
    
    def get_engine_info(self) -> dict:
        """
        Returns information about the PdfPlumber engine.
        
        Returns:
            dict: Engine information
        """
        try:
            import pdfplumber
            from PIL import Image
            
            return {
                "name": "pdfplumber+ReportLab",
                "version": {
                    "pdfplumber": getattr(pdfplumber, "__version__", "unknown"),
                    "pillow": Image.__version__
                },
                "description": "PdfPlumber with ReportLab for precise text extraction and direct PDF obfuscation",
                "features": [
                    "Precise text extraction with positioning",
                    "Direct PDF manipulation",
                    "Accurate coordinate mapping",
                    "High quality output",
                    "Table and form support"
                ],
                "supported_formats": ["PDF"],
                "obfuscation_methods": [
                    "Black rectangle masking"
                ]
            }
        except ImportError as e:
            return {
                "name": "pdfplumber+ReportLab",
                "version": "not installed",
                "description": "PdfPlumber with ReportLab - Not available",
                "error": str(e),
                "features": [],
                "supported_formats": []
            } 