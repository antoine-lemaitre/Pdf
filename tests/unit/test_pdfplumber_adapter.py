import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from src.adapters.pdfplumber_adapter import PdfPlumberAdapter
from src.adapters.local_storage_adapter import LocalStorageAdapter
from src.domain.entities import Document, Term, TermOccurrence, Position


class TestPdfPlumberAdapter:
    """Unit tests for PdfPlumberAdapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create PdfPlumberAdapter instance."""
        storage = LocalStorageAdapter()
        return PdfPlumberAdapter(storage)
    
    def test_get_engine_info(self, adapter):
        """Test engine info."""
        info = adapter.get_engine_info()
        
        assert info["name"] == "pdfplumber+Pillow"
        assert "version" in info
        assert "description" in info
        assert "features" in info
        assert "supported_formats" in info
    
    def test_group_words_by_columns_single_column(self, adapter):
        """Test grouping words by columns with single column."""
        words = [
            {"text": "word1", "x0": 10, "x1": 50, "top": 10, "bottom": 20},
            {"text": "word2", "x0": 10, "x1": 50, "top": 30, "bottom": 40},
            {"text": "word3", "x0": 10, "x1": 50, "top": 50, "bottom": 60}
        ]
        
        columns = adapter._group_words_by_columns(words)
        
        assert len(columns) == 1
        assert len(columns[0]) == 3
        assert columns[0][0]["text"] == "word1"
        assert columns[0][1]["text"] == "word2"
        assert columns[0][2]["text"] == "word3"
    
    def test_group_words_by_columns_multiple_columns(self, adapter):
        """Test grouping words by columns with multiple columns."""
        words = [
            {"text": "left1", "x0": 10, "x1": 50, "top": 10, "bottom": 20},
            {"text": "right1", "x0": 200, "x1": 250, "top": 10, "bottom": 20},
            {"text": "left2", "x0": 10, "x1": 50, "top": 30, "bottom": 40},
            {"text": "right2", "x0": 200, "x1": 250, "top": 30, "bottom": 40}
        ]
        
        columns = adapter._group_words_by_columns(words)
        
        assert len(columns) == 2
        assert len(columns[0]) == 2  # Left column
        assert len(columns[1]) == 2  # Right column
        assert columns[0][0]["text"] == "left1"
        assert columns[1][0]["text"] == "right1"
    
    def test_find_term_in_column_single_word(self, adapter):
        """Test finding single word term in column."""
        column_words = [
            {"text": "hello", "x0": 10, "x1": 50, "top": 10, "bottom": 20},
            {"text": "world", "x0": 10, "x1": 50, "top": 30, "bottom": 40}
        ]
        term_words = ["hello"]
        term_text = "hello"
        page_number = 1
        
        occurrences = adapter._find_term_in_column(column_words, term_words, term_text, page_number)
        
        assert len(occurrences) == 1
        assert occurrences[0].term.text == "hello"
        assert occurrences[0].page_number == 1
        assert occurrences[0].position.x0 == 10
        assert occurrences[0].position.x1 == 50
    
    def test_find_term_in_column_multi_word(self, adapter):
        """Test finding multi-word term in column."""
        column_words = [
            {"text": "hello", "x0": 10, "x1": 50, "top": 10, "bottom": 20},
            {"text": "world", "x0": 10, "x1": 50, "top": 10, "bottom": 20},
            {"text": "test", "x0": 10, "x1": 50, "top": 30, "bottom": 40}
        ]
        term_words = ["hello", "world"]
        term_text = "hello world"
        page_number = 1
        
        occurrences = adapter._find_term_in_column(column_words, term_words, term_text, page_number)
        
        assert len(occurrences) == 1
        assert occurrences[0].term.text == "hello world"
        assert occurrences[0].page_number == 1
    
    def test_find_term_in_column_no_match(self, adapter):
        """Test finding term that doesn't exist in column."""
        column_words = [
            {"text": "hello", "x0": 10, "x1": 50, "top": 10, "bottom": 20},
            {"text": "world", "x0": 10, "x1": 50, "top": 30, "bottom": 40}
        ]
        term_words = ["missing"]
        term_text = "missing"
        page_number = 1
        
        occurrences = adapter._find_term_in_column(column_words, term_words, term_text, page_number)
        
        assert len(occurrences) == 0
    
    def test_find_term_in_column_partial_word_match(self, adapter):
        """Test finding partial word match."""
        column_words = [
            {"text": "testing", "x0": 10, "x1": 70, "top": 10, "bottom": 20}
        ]
        term_words = ["test"]
        term_text = "test"
        page_number = 1
        
        occurrences = adapter._find_term_in_column(column_words, term_words, term_text, page_number)
        
        assert len(occurrences) == 1
        assert occurrences[0].term.text == "test"
        # Should calculate proportional position
        assert occurrences[0].position.x0 < occurrences[0].position.x1
    
    def test_extract_text_occurrences_single_word(self, adapter, sample_pdf):
        """Test text extraction for single word."""
        document = Document(path=sample_pdf)
        term = Term(text="test")
        
        occurrences = adapter.extract_text_occurrences(document, term)
        
        assert isinstance(occurrences, list)
        for occ in occurrences:
            assert isinstance(occ, TermOccurrence)
            assert occ.term.text == "test"
            assert isinstance(occ.position, Position)
            assert occ.page_number > 0
    
    def test_extract_text_occurrences_multi_word(self, adapter, sample_pdf):
        """Test text extraction for multi-word term."""
        document = Document(path=sample_pdf)
        term = Term(text="test document")
        
        occurrences = adapter.extract_text_occurrences(document, term)
        
        assert isinstance(occurrences, list)
        for occ in occurrences:
            assert isinstance(occ, TermOccurrence)
            assert occ.term.text == "test document"
            assert isinstance(occ.position, Position)
            assert occ.page_number > 0
    
    def test_extract_text_occurrences_case_insensitive(self, adapter, sample_pdf):
        """Test text extraction is case insensitive."""
        document = Document(path=sample_pdf)
        term = Term(text="TEST")
        
        occurrences = adapter.extract_text_occurrences(document, term)
        
        assert isinstance(occurrences, list)
        # Should find "test" even when searching for "TEST"
        assert len(occurrences) > 0
    
    def test_obfuscate_occurrences(self, adapter, sample_pdf, temp_output_path):
        """Test obfuscation functionality."""
        document = Document(path=sample_pdf)
        term = Term(text="test")
        
        # Extract occurrences first
        occurrences = adapter.extract_text_occurrences(document, term)
        assert len(occurrences) > 0
        
        # Obfuscate
        obfuscated_content = adapter.obfuscate_occurrences(document, occurrences)
        
        # Verify output
        assert isinstance(obfuscated_content, bytes)
        assert len(obfuscated_content) > 0
        
        # Save and verify file
        with open(temp_output_path, 'wb') as f:
            f.write(obfuscated_content)
        
        assert os.path.exists(temp_output_path)
        assert os.path.getsize(temp_output_path) > 0
    
    def test_obfuscate_occurrences_empty_list(self, adapter, sample_pdf):
        """Test obfuscation with empty occurrences list."""
        document = Document(path=sample_pdf)
        occurrences = []
        
        obfuscated_content = adapter.obfuscate_occurrences(document, occurrences)
        
        # Should still return a valid PDF
        assert isinstance(obfuscated_content, bytes)
        assert len(obfuscated_content) > 0 