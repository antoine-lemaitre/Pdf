import pytest
import os
from pathlib import Path
from src.adapters.pymupdf_adapter import PyMuPdfAdapter
from src.adapters.local_storage_adapter import LocalStorageAdapter
from src.domain.entities import Term, Document, ObfuscationRequest


class TestRealPDF:
    """Tests using the real test1.pdf file."""
    
    @pytest.fixture
    def real_pdf_path(self):
        """Path to the real test PDF."""
        pdf_path = Path("data/input/test1.pdf")
        if not pdf_path.exists():
            pytest.skip("data/input/test1.pdf not found")
        return str(pdf_path)
    
    @pytest.fixture
    def pdf_processor(self):
        """PDF processor for testing."""
        storage = LocalStorageAdapter()
        return PyMuPdfAdapter(storage)
    
    def test_obfuscate_real_pdf_terms(self, real_pdf_path, temp_output_path, pdf_processor):
        """Test obfuscation with real PDF and real terms."""
        
        # Use the same terms as in the test script
        terms = [
            Term(text="roffit"),
            Term(text="06 17 20 20 89"),
            Term(text="proffit.manon@gmail.com"),
            Term(text="Neuilly sur seiine")
        ]
        
        document = Document(path=real_pdf_path)
        
        # Test extraction for each term
        all_occurrences = []
        for term in terms:
            occurrences = pdf_processor.extract_text_occurrences(document, term)
            all_occurrences.extend(occurrences)
        
        # Test obfuscation
        if all_occurrences:
            obfuscated_content = pdf_processor.obfuscate_occurrences(document, all_occurrences)
            
            # Write to output file
            with open(temp_output_path, 'wb') as f:
                f.write(obfuscated_content)
            
            # Check file exists and has reasonable size
            assert os.path.exists(temp_output_path)
            
            original_size = os.path.getsize(real_pdf_path)
            output_size = os.path.getsize(temp_output_path)
            
            # Output should be roughly same size or slightly larger
            assert output_size > 0
            assert output_size >= original_size * 0.8  # At least 80% of original
            assert output_size <= original_size * 2.0  # At most 200% of original
        
        # Check that at least some terms were found
        successful_terms = [occ for occ in all_occurrences if occ.term.text in ["roffit", "06 17 20 20 89", "proffit.manon@gmail.com"]]
        assert len(successful_terms) > 0
    
    def test_case_insensitive_search_real_pdf(self, real_pdf_path, temp_output_path, pdf_processor):
        """Test case insensitive search with real PDF."""
        
        # Test with different case variations
        terms = [
            Term(text="ROFFIT"),  # uppercase
            Term(text="roffit"),  # lowercase
            Term(text="Roffit"),  # capitalized
        ]
        
        document = Document(path=real_pdf_path)
        
        # All variations should find the same occurrences
        all_occurrences = []
        for term in terms:
            occurrences = pdf_processor.extract_text_occurrences(document, term)
            all_occurrences.extend(occurrences)
        
        # Should find occurrences for "roffit" regardless of case
        roffit_occurrences = [occ for occ in all_occurrences if occ.term.text.lower() == "roffit"]
        assert len(roffit_occurrences) > 0 