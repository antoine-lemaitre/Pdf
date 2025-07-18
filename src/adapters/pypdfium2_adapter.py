"""
This adapter uses pypdfium2 for text extraction and PIL+ReportLab for obfuscation.
Robust implementation using raster approach for maximum compatibility.
"""
import io
import tempfile
import os
import pypdfium2 as pdfium
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from ..domain.entities import Document, Term, TermOccurrence, Position
from ..domain.exceptions import DocumentProcessingError
from ..ports.pdf_processor_port import PdfProcessorPort
from ..ports.file_storage_port import FileStoragePort
from typing import List


class PyPdfium2Adapter(PdfProcessorPort):
    """
    PyPDFium2 adapter for PDF processing with PIL+ReportLab obfuscation.
    """
    
    def __init__(self, file_storage: FileStoragePort):
        self._file_storage = file_storage

    def extract_text_occurrences(self, document: Document, term: Term) -> List[TermOccurrence]:
        """
        Extract text occurrences using PyPDFium2 with improved bounding boxes from text rects.
        """
        try:
            pdf_content = self._file_storage.read_file(document.path)
            pdf = pdfium.PdfDocument(pdf_content)
            occurrences = []
            
            for page_index in range(len(pdf)):
                page = pdf[page_index]
                text_page = page.get_textpage()
                text_page.count_rects()  # Indispensable pour get_rect/get_index
                
                # Search for the term
                searcher = text_page.search(term.text, match_case=False, match_whole_word=False)
                
                # Get unique occurrences
                seen = set()
                unique_results = []
                result_index = 0
                while True:
                    result = searcher.get_next()
                    if result is None:
                        break
                    start_index, count = result
                    
                    # Get charbox for the full match (word)
                    char_left, char_bottom, char_right, char_top = text_page.get_charbox(start_index, loose=True)
                    if count > 1:
                        end_left, end_bottom, end_right, end_top = text_page.get_charbox(start_index + count - 1, loose=True)
                        char_left = min(char_left, end_left)
                        char_right = max(char_right, end_right)
                        char_top = max(char_top, end_top)
                        char_bottom = min(char_bottom, end_bottom)

                    # Use only charbox coordinates - simple and direct approach
                    # For each word, use the bounding box of all its characters
                    left = min(char_left, char_right)
                    right = max(char_left, char_right)
                    top = max(char_top, char_bottom)
                    bottom = min(char_top, char_bottom)
                    
                    coord_tuple = (left, bottom, right, top)
                    if coord_tuple not in seen:
                        seen.add(coord_tuple)
                        unique_results.append((start_index, count, left, bottom, right, top))
                    result_index += 1
                searcher.close()
                
                # Create occurrences
                for start_index, count, left, bottom, right, top in unique_results:
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
                
                text_page.close()
            pdf.close()
            return occurrences
        except Exception as e:
            raise DocumentProcessingError(f"Failed to extract text with pypdfium2: {str(e)}")

    def obfuscate_occurrences(self, document: Document, occurrences: List[TermOccurrence]) -> bytes:
        """
        Obfuscate using pypdfium2 rendering and PIL+ReportLab image processing.
        Robust raster-based approach for maximum compatibility.
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
                
                # Get page dimensions and bbox information
                page_width = page.get_width()
                page_height = page.get_height()
                
                # Get bbox information from pypdfium2
                try:
                    bbox_x0, bbox_y0, bbox_x1, bbox_y1 = page.get_mediabox()
                    print(f"DEBUG: pypdfium2 mediabox: ({bbox_x0}, {bbox_y0}, {bbox_x1}, {bbox_y1})")
                except:
                    # Fallback to page dimensions
                    bbox_x0, bbox_y0, bbox_x1, bbox_y1 = 0, 0, page_width, page_height
                    print(f"DEBUG: pypdfium2 fallback bbox: ({bbox_x0}, {bbox_y0}, {bbox_x1}, {bbox_y1})")
                
                print(f"DEBUG: pypdfium2 page dimensions: {page_width}x{page_height}")
                print(f"DEBUG: pypdfium2 bbox: ({bbox_x0}, {bbox_y0}, {bbox_x1}, {bbox_y1})")
                
                # Render page as high-resolution image
                scale = 2.0
                bitmap = page.render(scale=scale, optimize_mode="print")
                pil_image = bitmap.to_pil()
                
                # Calculate scale factors
                img_w, img_h = pil_image.size
                scale_x = img_w / page_width
                scale_y = img_h / page_height
                
                # Draw black rectangles for obfuscation
                draw = ImageDraw.Draw(pil_image)
                
                for occ in occ_by_page.get(page_index, []):
                    print(f"DEBUG: pypdfium2 term '{occ.term.text}' - coords: x0={occ.position.x0}, y0={occ.position.y0}, x1={occ.position.x1}, y1={occ.position.y1}")
                    
                    # Apply bbox offset adjustment (same logic as pdfplumber)
                    x0_adjusted = occ.position.x0 - bbox_x0
                    y0_adjusted = occ.position.y0 - bbox_y0
                    x1_adjusted = occ.position.x1 - bbox_x0
                    y1_adjusted = occ.position.y1 - bbox_y0
                    
                    print(f"DEBUG: pypdfium2 adjusted coords: x0={x0_adjusted}, y0={y0_adjusted}, x1={x1_adjusted}, y1={y1_adjusted}")
                    
                    # Convert PDF coordinates to image coordinates
                    x0 = x0_adjusted * scale_x
                    y0 = img_h - (y1_adjusted * scale_y)  # Invert Y axis
                    x1 = x1_adjusted * scale_x
                    y1 = img_h - (y0_adjusted * scale_y)  # Invert Y axis
                    
                    # Ensure coordinates are in correct order
                    x0, x1 = min(x0, x1), max(x0, x1)
                    y0, y1 = min(y0, y1), max(y0, y1)
                    
                    # Add bbox offset to rectangle height for better coverage
                    bbox_offset = abs(bbox_y0)  # Value absolute of bbox offset
                    height_adjustment = bbox_offset * scale_y
                    y0 -= height_adjustment / 2  # Extend up
                    y1 += height_adjustment / 2  # Extend down
                    
                    print(f"DEBUG: pypdfium2 image coords: x0={x0}, y0={y0}, x1={x1}, y1={y1}")
                    print(f"DEBUG: pypdfium2 bbox offset: {bbox_offset}, height adjustment: {height_adjustment}")
                    
                    # Draw black rectangle
                    draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0))
                
                # Convert PIL image to PDF using ReportLab
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
                "license": "Apache 2.0",
                "description": "pypdfium2 with PIL+ReportLab for robust raster-based obfuscation"
            }
        except ImportError:
            return {
                "name": "pypdfium2+PIL+ReportLab",
                "version": "not installed",
                "license": "Apache 2.0",
                "description": "pypdfium2 with PIL+ReportLab for robust raster-based obfuscation"
            } 