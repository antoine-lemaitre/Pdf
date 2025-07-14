#!/usr/bin/env python3
"""
PDF Obfuscation Service.
Supports CLI and server modes.
"""
import sys
import argparse

from src.adapters.fastapi_adapter import app
from src.cli import main as cli_main


def server_mode(host: str, port: int):
    """Launch the FastAPI server."""
    import uvicorn
    
    print(f"Starting server on {host}:{port}")
    print(f"API Documentation: http://{host}:{port}/docs")
    
    uvicorn.run(app, host=host, port=port, log_level="info")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="PDF Obfuscator Service")
    subparsers = parser.add_subparsers(dest="mode", help="Execution mode")
    
    # Server mode
    server_parser = subparsers.add_parser("server", help="Launch the API server")
    server_parser.add_argument("--host", default="127.0.0.1", help="Server IP address")
    server_parser.add_argument("--port", type=int, default=8000, help="Server port")
    
    # CLI mode
    cli_parser = subparsers.add_parser("cli", help="Command line mode")
    cli_parser.add_argument("document", help="Path to the PDF document")
    cli_parser.add_argument("--terms", nargs="+", required=True, help="Terms to obfuscate")
    cli_parser.add_argument("--output", help="Output file (optional)")
    cli_parser.add_argument("--engine", default="pymupdf", choices=["pymupdf", "pypdfium2"], help="Obfuscation engine")
    cli_parser.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
    cli_parser.add_argument("--engines", action="store_true", help="List available engines")
    cli_parser.add_argument("--validate", action="store_true", help="Validate document only")
    cli_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose mode")
    
    args = parser.parse_args()
    
    if args.mode == "server":
        server_mode(args.host, args.port)
    elif args.mode == "cli":
        sys.argv = ["main.py"] + sys.argv[2:]  # Adjust arguments for CLI
        return cli_main()
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 