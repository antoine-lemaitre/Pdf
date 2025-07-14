"""
This adapter uses pypdfium2 for text extraction and PIL+ReportLab for high-quality masking.
Based on StackOverflow solution for preserving PDF quality with PIL.
"""
import os
from typing import List, Optional
import tempfile
import io
import logging

try:
    import pypdfium2 as pdfium
except ImportError:
    raise ImportError("pypdfium2 is required. Install with: pip install pypdfium2")

try:
    from PIL import Image, ImageDraw
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
except ImportError:
    raise ImportError("PIL and reportlab are required. Install with: pip install Pillow reportlab")

from src.ports.pdf_processor_port import PdfProcessorPort
from src.ports.file_storage_port import FileStoragePort
from src.domain.entities import Document, Term, TermOccurrence, ObfuscationResult, TermResult, ProcessingStatus, Position
from src.domain.exceptions import DocumentProcessingError

class PyPdfium2Adapter(PdfProcessorPort):
    """PDF processor using pypdfium2 for text extraction and PIL+ReportLab for high-quality masking."""
    
    def __init__(self, file_storage: FileStoragePort):
        self._file_storage = file_storage
    
    def extract_text_occurrences(self, document: Document, term: Term) -> List[TermOccurrence]:
        try:
            pdf_content = self._file_storage.read_file(document.path)
            pdf = pdfium.PdfDocument(pdf_content)
            occurrences = []
            for page_index in range(len(pdf)):
                page = pdf[page_index]
                text_page = page.get_textpage()
                searcher = text_page.search(term.text, match_case=False)
                while True:
                    result = searcher.get_next()
                    if result is None:
                        break
                    start_index, count = result
                    
                    # Get coordinates of first character
                    left, bottom, right, top = text_page.get_charbox(start_index)
                    
                    # If multiple characters, get coordinates of last character too
                    if count > 1:
                        end_index = start_index + count - 1
                        end_left, end_bottom, end_right, end_top = text_page.get_charbox(end_index)
                        # Use the full width from first to last character
                        right = end_right
                        # Use the maximum height to cover all characters
                        top = max(top, end_top)
                        bottom = min(bottom, end_bottom)
                    
                    # Add some padding to better cover the text
                    padding = 1.0  # 1 point padding
                    left = max(0, left - padding)
                    right = right + padding
                    bottom = max(0, bottom - padding)
                    top = top + padding
                    
                    occurrence = TermOccurrence(
                        term=term,
                        position=Position(
                            x0=left,
                            y0=bottom,
                            x1=right,
                            y1=top
                        ),
                        page_number=page_index + 1
                    )
                    occurrences.append(occurrence)
                searcher.close()
                text_page.close()
            pdf.close()
            return occurrences
        except Exception as e:
            raise DocumentProcessingError(f"Failed to extract text with pypdfium2: {str(e)}")

    def obfuscate_occurrences(self, document: Document, occurrences: List[TermOccurrence]) -> bytes:
        """
        Obfuscate using PIL+ReportLab approach for high-quality masking.
        Renders each page as high-resolution image, draws black rectangles, then converts to PDF.
        """
        try:
            pdf_content = self._file_storage.read_file(document.path)
            pdf = pdfium.PdfDocument(pdf_content)
            
            # Group occurrences by page
            occ_by_page = {}
            for occ in occurrences:
                occ_by_page.setdefault(occ.page_number - 1, []).append(occ)
            
            # Create output PDF with ReportLab
            output_buffer = io.BytesIO()
            c = canvas.Canvas(output_buffer)
            
            for page_index in range(len(pdf)):
                page = pdf[page_index]
                
                # Get page dimensions
                page_width = page.get_width()
                page_height = page.get_height()
                
                # Render page as high-resolution image (2x for better quality)
                scale = 2.0
                pil_image = page.render(scale=scale, optimize_mode="print").to_pil()
                
                # Draw black rectangles on the image
                draw = ImageDraw.Draw(pil_image)
                
                for occ in occ_by_page.get(page_index, []):
                    # Convert PDF coordinates to image coordinates
                    # PDF origin: bottom-left, PIL: top-left
                    img_w, img_h = pil_image.size
                    scale_x = img_w / page_width
                    scale_y = img_h / page_height
                    
                    x0 = occ.position.x0 * scale_x
                    x1 = occ.position.x1 * scale_x
                    # Invert Y coordinates and adjust positioning
                    y0 = img_h - (occ.position.y1 * scale_y)
                    y1 = img_h - (occ.position.y0 * scale_y)
                    
                    # Add vertical offset to move rectangles down (they are too high)
                    vertical_offset = 8 * scale_y  # 8 points down (was 5)
                    y0 = min(img_h, y0 + vertical_offset)
                    y1 = min(img_h, y1 + vertical_offset)
                    
                    # Add padding to better cover the text
                    padding = 2 * scale_y  # 2 points of padding, scaled
                    y0 = max(0, y0 - padding)  # Move up
                    y1 = min(img_h, y1 + padding)  # Move down
                    
                    # Ensure minimum height for visibility
                    min_height = 3 * scale_y
                    if y1 - y0 < min_height:
                        y1 = y0 + min_height
                    
                    # Draw black rectangle
                    draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0))
                
                # Convert PIL image to PDF using ReportLab (high quality)
                img_buffer = io.BytesIO()
                pil_image.save(img_buffer, format='PNG', optimize=False)
                img_buffer.seek(0)
                
                # Add image to PDF page
                c.setPageSize((page_width, page_height))
                c.drawImage(ImageReader(img_buffer), 0, 0, page_width, page_height)
                
                # Add page break if not the last page
                if page_index < len(pdf) - 1:
                    c.showPage()
            
            # Save the PDF
            c.save()
            pdf.close()
            
            return output_buffer.getvalue()
            
        except Exception as e:
            raise DocumentProcessingError(f"Failed to obfuscate with pypdfium2+PIL+ReportLab: {str(e)}")

    def get_engine_info(self) -> dict:
        try:
            import pypdfium2
            version = getattr(pypdfium2, "__version__", "unknown")
            return {
                "name": "pypdfium2+PIL+ReportLab",
                "version": version,
                "license": "Apache 2.0 + PIL + BSD",
                "description": "pypdfium2 for text extraction + PIL+ReportLab for high-quality masking"
            }
        except ImportError:
            return {
                "name": "pypdfium2+PIL+ReportLab",
                "version": "not installed",
                "license": "Apache 2.0 + PIL + BSD",
                "description": "pypdfium2 for text extraction + PIL+ReportLab for high-quality masking"
            } 