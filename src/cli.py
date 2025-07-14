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
        description="Obfuscate terms in a PDF document",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s document.pdf --terms "John Doe" "123-45-6789"
    %(prog)s input.pdf --terms "secret" --output output.pdf
    %(prog)s --validate document.pdf
        """
    )
    
    parser.add_argument(
        "document",
        nargs="?",
        help="Path to the PDF document to process (optional for --engines)"
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
        choices=["pymupdf", "pypdfium2"],
        help="Obfuscation engine to use (default: pymupdf)"
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
    
    # Initialize application
    app = PdfObfuscationApplication()
    
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
        
        # Execute obfuscation
        result = app.obfuscate_document(
            source_path=args.document,
            terms=args.terms,
            destination_path=args.output,
            engine=args.engine
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