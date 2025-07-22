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
    from pdf2image import convert_from_bytes
except ImportError:
    raise ImportError("pdfplumber, pdf2image, and Pillow are required. Install with: pip install pdfplumber pdf2image Pillow")

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
                    
                    # Handle both single terms and multi-word terms
                    term_text = term.text.lower()
                    term_words = term.text.split()
                    
                    if len(term_words) == 1:
                        # Single word/part of word search - use substring matching
                        for word in words:
                            if term_text in word['text'].lower():
                                # Found a word containing our term
                                # Calculate precise coordinates for the substring using proportional positioning
                                word_text = word['text']
                                term_pos = word_text.lower().find(term_text)
                                
                                if term_pos != -1:
                                    # Calculate proportional width of the term within the word
                                    word_width = word['x1'] - word['x0']
                                    term_width = len(term_text) / len(word_text) * word_width
                                    
                                    # Calculate the starting position of the term
                                    term_start_ratio = term_pos / len(word_text)
                                    term_x0 = word['x0'] + (term_start_ratio * word_width)
                                    term_x1 = term_x0 + term_width
                                    
                                    x0, y0, x1, y1 = term_x0, word['top'], term_x1, word['bottom']
                                else:
                                    # Fallback to word bounds if term not found
                                    x0, y0, x1, y1 = word['x0'], word['top'], word['x1'], word['bottom']
                                
                                position = Position(x0=x0, y0=y0, x1=x1, y1=y1)
                                
                                occurrence = TermOccurrence(
                                    term=term,
                                    position=position,
                                    page_number=page_num + 1
                                )
                                occurrences.append(occurrence)
                    else:
                        # Multi-word search - handle both single-line and multi-line terms
                        # First try consecutive words on same line
                        consecutive_found = False
                        for i in range(len(words) - len(term_words) + 1):
                            # Check if the next words match our term
                            match = True
                            for j, term_word in enumerate(term_words):
                                if i + j >= len(words) or words[i + j]['text'].lower() != term_word.lower():
                                    match = False
                                    break
                            
                            if match:
                                # Found consecutive words that match our term
                                consecutive_found = True
                                
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
                        
                        # If consecutive words not found, try multi-line search with column awareness
                        if not consecutive_found:
                            # Group words by columns to avoid mixing content from different columns
                            columns = self._group_words_by_columns(words)
                            
                            # Search within each column separately
                            for column_words in columns:
                                if len(column_words) >= len(term_words):
                                    # Try to find the term within this column
                                    column_occurrences = self._find_term_in_column(column_words, term_words, term_text, page_num + 1)
                                    occurrences.extend(column_occurrences)
            
            return occurrences
            
        except Exception as e:
            raise DocumentProcessingError(f"Error during text extraction with pdfplumber: {str(e)}")
    
    def _group_words_by_columns(self, words: List[dict]) -> List[List[dict]]:
        """
        Group words by columns based on their x-coordinates to avoid mixing content from different columns.
        
        Args:
            words: List of word dictionaries from pdfplumber
            
        Returns:
            List of word lists, each representing a column
        """
        if not words:
            return []
        
        # Sort words by x-coordinate to identify column boundaries
        sorted_words = sorted(words, key=lambda w: w['x0'])
        
        # Find column boundaries by looking for large gaps in x-coordinates
        columns = []
        current_column = [sorted_words[0]]
        
        for i in range(1, len(sorted_words)):
            current_word = sorted_words[i]
            prev_word = sorted_words[i-1]
            
            # If there's a large gap in x-coordinate, it's likely a new column
            gap = current_word['x0'] - prev_word['x1']
            if gap > 50:  # Threshold for column separation (adjust as needed)
                if current_column:
                    columns.append(current_column)
                current_column = [current_word]
            else:
                current_column.append(current_word)
        
        if current_column:
            columns.append(current_column)
        
        # Sort words within each column by position (top to bottom, left to right)
        for column in columns:
            column.sort(key=lambda w: (w['top'], w['x0']))
        
        return columns
    
    def _find_term_in_column(self, column_words: List[dict], term_words: List[str], term_text: str, page_number: int) -> List[TermOccurrence]:
        """
        Find a multi-line term within a single column of words.
        
        Args:
            column_words: Words in a single column
            term_words: Individual words of the term to search for
            term_text: Full term text
            page_number: Page number
            
        Returns:
            List of TermOccurrence objects
        """
        occurrences = []
        
        # Find all words that match any part of our term
        matching_word_indices = []
        for i, word in enumerate(column_words):
            word_text = word['text'].lower()
            for term_word in term_words:
                if term_word.lower() in word_text or word_text in term_word.lower():
                    matching_word_indices.append(i)
        
        # Try to find sequences of matching words that form our term
        if len(matching_word_indices) >= len(term_words):
            # Get matching words in order
            matching_words = [column_words[i] for i in matching_word_indices]
            
            # Try to find consecutive sequences that match our term
            for i in range(len(matching_words) - len(term_words) + 1):
                sequence = matching_words[i:i + len(term_words)]
                
                # Check if this sequence matches our term
                sequence_text = ' '.join(w['text'].lower() for w in sequence)
                if term_text in sequence_text or sequence_text in term_text:
                    # Calculate bounding box from all words in sequence
                    x0 = min(word['x0'] for word in sequence)
                    y0 = min(word['top'] for word in sequence)
                    x1 = max(word['x1'] for word in sequence)
                    y1 = max(word['bottom'] for word in sequence)
                    
                    position = Position(x0=x0, y0=y0, x1=x1, y1=y1)
                    
                    occurrence = TermOccurrence(
                        term=Term(term_text),  # Create a new Term object
                        position=position,
                        page_number=page_number
                    )
                    occurrences.append(occurrence)
        
        return occurrences
    

    
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
            
            # Convert back to PDF using Pillow
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
            
            # Add bbox offset height to rectangle for better coverage
            bbox_offset_height = abs(bbox_y0)  # Absolute value of bbox offset
            bbox_offset_pixels = int(bbox_offset_height * scale_y)
            
            # Extend rectangle height only above (not below)
            y0_img = max(0, y0_img - bbox_offset_pixels)
            
            # Apply obfuscation
            draw.rectangle([x0, y0_img, x1, y1_img], fill=(0, 0, 0))
        
        return processed_image
    
    def _images_to_pdf(self, images: List[Image.Image]) -> bytes:
        """
        Convert list of PIL images back to PDF using Pillow.
        Preserves original page dimensions.
        
        Args:
            images: List of PIL Images
            
        Returns:
            bytes: PDF content
        """
        # Convert images to PDF using Pillow with original dimensions
        if len(images) == 1:
            # Single page - preserve original dimensions
            output_buffer = io.BytesIO()
            # Convert to RGB if needed (PDF requires RGB)
            if images[0].mode != 'RGB':
                images[0] = images[0].convert('RGB')
            images[0].save(output_buffer, format='PDF', resolution=200.0)
            output_buffer.seek(0)
            return output_buffer.getvalue()
        else:
            # Multiple pages - preserve original dimensions
            output_buffer = io.BytesIO()
            # Convert all images to RGB if needed
            rgb_images = []
            for img in images:
                if img.mode != 'RGB':
                    rgb_images.append(img.convert('RGB'))
                else:
                    rgb_images.append(img)
            
            rgb_images[0].save(
                output_buffer, 
                format='PDF', 
                save_all=True, 
                append_images=rgb_images[1:],
                resolution=200.0
            )
            output_buffer.seek(0)
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
                "name": "pdfplumber+Pillow",
                "version": {
                    "pdfplumber": getattr(pdfplumber, "__version__", "unknown"),
                    "pillow": Image.__version__
                },
                "description": "PdfPlumber with Pillow for precise text extraction and raster-based obfuscation",
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
                "name": "pdfplumber+Pillow",
                "version": "not installed",
                "description": "PdfPlumber with Pillow - Not available",
                "error": str(e),
                "features": [],
                "supported_formats": []
            } 