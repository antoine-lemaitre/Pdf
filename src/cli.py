#!/usr/bin/env python3
"""
CLI interface for PDF obfuscation service.
"""
import argparse
import sys
import json
from pathlib import Path
from typing import List

from src.application.pdf_obfuscation_app import PdfObfuscationApplication


def main():
    """Main entry point for CLI interface."""
    parser = argparse.ArgumentParser(
        description="Obfuscate terms in a PDF document or evaluate obfuscation quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s document.pdf --terms "John Doe" "123-45-6789"
    %(prog)s input.pdf --terms "secret" --output output.pdf
    %(prog)s --validate document.pdf
    %(prog)s --evaluate-quality original.pdf obfuscated.pdf --terms "John Doe"
        """
    )
    
    parser.add_argument(
        "document",
        nargs="?",
        help="Path to the PDF document to process (optional for --engines or --evaluate-quality)"
    )
    
    parser.add_argument(
        "obfuscated_document",
        nargs="?",
        help="Path to the obfuscated PDF document (required for --evaluate-quality)"
    )
    
    parser.add_argument(
        "--terms", "-t",
        nargs="+",
        help="Terms to obfuscate in the document"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output path for the obfuscated document (optional)"
    )
    
    parser.add_argument(
        "--engine", "-e",
        default="pymupdf",
        choices=["pymupdf", "pypdfium2", "pdfplumber"],
        help="Obfuscation engine to use (default: pymupdf)"
    )
    
    parser.add_argument(
        "--evaluator",
        choices=["tesseract", "mistral"],
        default="tesseract",
        help="Quality evaluator to use (default: tesseract)"
    )
    
    parser.add_argument(
        "--evaluate-quality",
        action="store_true",
        help="Evaluate quality after obfuscation or evaluate quality of existing obfuscated document"
    )
    
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Only validate the document without obfuscating it"
    )
    
    parser.add_argument(
        "--engines",
        action="store_true",
        help="Show available engines"
    )
    
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose mode"
    )
    
    args = parser.parse_args()
    
    # Initialize application with chosen evaluator
    if args.evaluator == "mistral":
        from src.adapters.mistral_text_extractor import MistralTextExtractor
        from src.adapters.quality_evaluator import QualityEvaluator
        from src.adapters.local_storage_adapter import LocalStorageAdapter
        
        file_storage = LocalStorageAdapter()
        mistral_extractor = MistralTextExtractor(file_storage)
        mistral_evaluator = QualityEvaluator(mistral_extractor)
        app = PdfObfuscationApplication(
            file_storage=file_storage,
            quality_evaluator=mistral_evaluator
        )
    else:
        # Default Tesseract evaluator
        from src.adapters.tesseract_text_extractor import TesseractTextExtractor
        from src.adapters.quality_evaluator import QualityEvaluator
        from src.adapters.local_storage_adapter import LocalStorageAdapter
        
        file_storage = LocalStorageAdapter()
        tesseract_extractor = TesseractTextExtractor(file_storage)
        tesseract_evaluator = QualityEvaluator(tesseract_extractor)
        app = PdfObfuscationApplication(
            file_storage=file_storage,
            quality_evaluator=tesseract_evaluator
        )
    
    try:
        # Command to list engines
        if args.engines:
            engines = app.get_supported_engines()
            if args.format == "json":
                print(json.dumps({"engines": engines}, indent=2))
            else:
                print("Available obfuscation engines:")
                for engine in engines:
                    print(f"  - {engine}")
            return 0
        
        # Document validation
        if args.validate:
            if not args.document:
                print("Error: A document must be specified for validation", file=sys.stderr)
                return 1
            is_valid = app.validate_document(args.document)
            if args.format == "json":
                print(json.dumps({"valid": is_valid, "document": args.document}))
            else:
                status = "valid" if is_valid else "invalid"
                print(f"Document {args.document}: {status}")
            return 0 if is_valid else 1
        
        # Quality evaluation mode (independent)
        if args.evaluate_quality and args.obfuscated_document:
            if not args.document:
                print("Error: Original document must be specified for quality evaluation", file=sys.stderr)
                return 1
            if not args.terms:
                print("Error: Terms must be specified for quality evaluation", file=sys.stderr)
                return 1
            if not Path(args.document).exists():
                print(f"Error: Original file {args.document} does not exist", file=sys.stderr)
                return 1
            if not Path(args.obfuscated_document).exists():
                print(f"Error: Obfuscated file {args.obfuscated_document} does not exist", file=sys.stderr)
                return 1
            
            if args.verbose:
                print(f"Evaluating quality:")
                print(f"  Original document: {args.document}")
                print(f"  Obfuscated document: {args.obfuscated_document}")
                print(f"  Terms: {', '.join(args.terms)}")
            
            # Execute quality evaluation
            result = app.evaluate_quality(
                original_document_path=args.document,
                obfuscated_document_path=args.obfuscated_document,
                terms_to_obfuscate=args.terms
            )
            
            # Display quality evaluation results
            if args.format == "json":
                # Get OCR execution times from details
                completeness_details = result.metrics.details.get('completeness', {}).get('details', {})
                original_ocr_time = completeness_details.get('original_ocr_time', 'N/A')
                obfuscated_ocr_time = completeness_details.get('obfuscated_ocr_time', 'N/A')
                
                output_data = {
                    "overall_score": result.metrics.overall_score,
                    "completeness_score": result.metrics.completeness_score,
                    "precision_score": result.metrics.precision_score,
                    "visual_integrity_score": result.metrics.visual_integrity_score,
                    "timestamp": result.timestamp,
                    "details": result.metrics.details,
                    "ocr_execution_times": {
                        "original_document": original_ocr_time,
                        "obfuscated_document": obfuscated_ocr_time
                    }
                }
                print(json.dumps(output_data, indent=2))
            else:
                print(f"Quality evaluation completed. Overall score: {result.metrics.overall_score}")
                print(f"Completeness: {result.metrics.completeness_score}")
                print(f"Precision: {result.metrics.precision_score}")
                print(f"Visual Integrity: {result.metrics.visual_integrity_score}")
                
                # Display details
                if result.metrics.details:
                    print("\nDetails:")
                    
                    # Completeness details
                    if 'completeness' in result.metrics.details:
                        comp_details = result.metrics.details['completeness']
                        print(f"  Completeness Details:")
                        print(f"    Total terms found: {comp_details.get('total_terms_found', 'N/A')}")
                        print(f"    Successfully obfuscated: {comp_details.get('successfully_obfuscated', 'N/A')}")
                        if comp_details.get('remaining_terms'):
                            print(f"    Remaining terms: {comp_details['remaining_terms']}")
                    
                    # Precision details
                    if 'precision' in result.metrics.details:
                        prec_details = result.metrics.details['precision']
                        print(f"  Precision Details:")
                        print(f"    Total original words: {prec_details.get('total_original_words', 'N/A')}")
                        print(f"    Words found: {prec_details.get('words_found', 'N/A')}")
                        if prec_details.get('missing_words'):
                            print(f"    Missing words: {prec_details['missing_words']}")
                    
                    # Visual integrity details
                    if 'visual_integrity' in result.metrics.details:
                        vis_details = result.metrics.details['visual_integrity']
                        print(f"  Visual Integrity Details:")
                        print(f"    Page count match: {vis_details.get('page_count_match', 'N/A')}")
                        print(f"    Dimension matches: {vis_details.get('dimension_matches', 'N/A')}")
                        if vis_details.get('size_differences'):
                            print(f"    Size differences: {vis_details['size_differences']}")
            
            return 0
        
        # Argument checks for obfuscation
        if not args.document:
            print("Error: A document must be specified for obfuscation", file=sys.stderr)
            return 1
            
        if not args.terms:
            print("Error: At least one term must be specified with --terms", file=sys.stderr)
            return 1
        
        if not Path(args.document).exists():
            print(f"Error: File {args.document} does not exist", file=sys.stderr)
            return 1
        
        if args.verbose:
            print(f"Processing document: {args.document}")
            print(f"Terms to obfuscate: {', '.join(args.terms)}")
            print(f"Engine: {args.engine}")
            if args.evaluate_quality:
                print("Quality evaluation: enabled")
        
        # Execute obfuscation
        result = app.obfuscate_document(
            source_path=args.document,
            terms=args.terms,
            destination_path=args.output,
            engine=args.engine,
            evaluate_quality=args.evaluate_quality
        )
        
        # Display results
        if args.format == "json":
            # JSON output
            output_data = {
                "success": result.success,
                "message": result.message,
                "output_document": result.output_document.path if result.output_document else None,
                "total_terms_processed": result.total_terms_processed,
                "total_occurrences_obfuscated": result.total_occurrences_obfuscated,
                "term_results": [
                    {
                        "term": tr.term.text,
                        "status": tr.status.value,
                        "occurrences_count": tr.occurrences_count,
                        "message": tr.message
                    }
                    for tr in result.term_results
                ],
                "error": result.error
            }
            print(json.dumps(output_data, indent=2))
        else:
            # Text output
            print(f"Status: {'Success' if result.success else 'Failed'}")
            if result.message:
                print(f"Message: {result.message}")
            if result.output_document:
                print(f"Output: {result.output_document.path}")
            print(f"Terms processed: {result.total_terms_processed}")
            print(f"Occurrences obfuscated: {result.total_occurrences_obfuscated}")
            
            if result.term_results:
                print("\nDetails by term:")
                for tr in result.term_results:
                    status_icon = "✅" if tr.status.value == "success" else "❌"
                    print(f"  {status_icon} '{tr.term.text}': {tr.occurrences_count} occurrences - {tr.message}")
            
            if result.error:
                print(f"Error: {result.error}")
        
        return 0 if result.success else 1
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main()) 