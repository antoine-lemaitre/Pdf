# PDF Obfuscation Service

A PDF document obfuscation service with hexagonal architecture, supporting CLI and REST API modes.

## 🏗️ Architecture

This project follows a **hexagonal architecture (ports and adapters)** to clearly separate business logic from implementation details:

```
src/
├── domain/               # Business core - Pure logic without dependencies
│   ├── entities.py      # Business entities (Document, Term, ObfuscationResult...)
│   ├── services/        # Business services
│   └── exceptions.py    # Business exceptions
├── ports/               # Interfaces - Contracts between domain and adapters
│   ├── pdf_processor_port.py    # Interface for PDF processing
│   ├── file_storage_port.py     # Interface for file storage
│   └── quality_evaluator_port.py # Interface for quality evaluation
├── adapters/            # Implementations - Technical details
│   ├── pymupdf_adapter.py       # PyMuPDF implementation
│   ├── pypdfium2_adapter.py     # PyPDFium2 implementation
│   ├── pdfplumber_adapter.py    # pdfplumber implementation
│   ├── tesseract_text_extractor.py # Tesseract OCR implementation
│   ├── mistral_text_extractor.py # Mistral AI OCR implementation
│   ├── local_storage_adapter.py # Local storage
│   ├── s3_storage_adapter.py    # S3 storage
│   └── fastapi_adapter.py       # REST web interface
├── application/         # Coordination - Application entry point
│   ├── pdf_obfuscation_app.py
│   └── pdf_processor_factory.py
└── cli.py              # Command line interface
```

### Benefits of this architecture

- **Testability**: Each layer can be tested independently
- **Flexibility**: Easy to add new PDF engines or storage systems
- **Maintainability**: Clear separation of responsibilities
- **Scalability**: Business logic protected from technical changes

## 🚀 Installation

### Prerequisites

- Python 3.12+
- uv (package manager)
- **System dependencies:**
  - **Tesseract OCR** (for quality evaluation):
    - macOS: `brew install tesseract`
    - Ubuntu/Debian: `sudo apt install tesseract-ocr`
    - Windows: Download from [GitHub releases](https://github.com/UB-Mannheim/tesseract/wiki)
  - **Poppler** (for PDF processing):
    - macOS: `brew install poppler`
    - Ubuntu/Debian: `sudo apt install poppler-utils`
    - Windows: Download from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases/)

### Installing dependencies

```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Install development dependencies
uv sync --extra dev
```


## 📋 Usage

The service can be used in CLI or API server mode.

### CLI Mode

```bash
# Obfuscate terms in a PDF (PyMuPDF by default)
uv run python main.py document.pdf --terms "John Doe" "123-45-6789"

# Specify an output file
uv run python main.py input.pdf --terms "confidential" --output output.pdf

# Obfuscate with quality evaluation
uv run python main.py document.pdf --terms "John Doe" --evaluate-quality

# Evaluate quality of existing obfuscation
uv run python main.py evaluate-quality original.pdf obfuscated.pdf --terms "John Doe"

# Validate a document
uv run python main.py --validate document.pdf

# Show available engines
uv run python main.py --engines

# Verbose mode with JSON output
uv run python main.py document.pdf --terms "secret" --verbose --format json
```

### API Server Mode

```bash
# Start the server
uv run python main.py server

# With custom configuration
uv run python main.py server --host 0.0.0.0 --port 8000
```

### REST API

Once the server is started, the API is available at `http://localhost:8000`

#### Interactive documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

#### Available endpoints

```bash
# Service health
GET /health

# Available engines
GET /engines

# Obfuscation via JSON
POST /obfuscate
# JSON: {"source_path": "...", "terms": [...], "engine": "pymupdf", "evaluate_quality": true}

# Quality evaluation
POST /evaluate-quality
# JSON: {"original_document_path": "...", "obfuscated_document_path": "...", "terms": [...], "engine_used": "pymupdf"}
```

### API usage examples

```bash
# Obfuscation via JSON (local file) with quality evaluation
curl -X POST "http://localhost:8000/obfuscate" \
  -H "Content-Type: application/json" \
  -d '{
    "source_path": "/path/to/document.pdf",
    "terms": [{"text": "confidential"}, {"text": "secret"}],
    "destination_path": "/path/to/output.pdf",
    "engine": "pymupdf",
    "evaluate_quality": true
  }'

# Quality evaluation
curl -X POST "http://localhost:8000/evaluate-quality" \
  -H "Content-Type: application/json" \
  -d '{
    "original_document_path": "/path/to/original.pdf",
    "obfuscated_document_path": "/path/to/obfuscated.pdf",
    "terms": [{"text": "John Doe"}, {"text": "123-45-6789"}],
    "engine_used": "pymupdf"
  }'
```

## 🔧 Configuration

### Obfuscation engines

Currently supported:
- **PyMuPDF**: Main engine, uses gray rectangles to mask text (AGPL license)
- **PyPDFium2**: Alternative engine with different obfuscation method
- **pdfplumber**: Text-based obfuscation engine

### Quality Evaluation

The system provides three metrics (0.0 to 1.0 scale):
- **Completeness**: All target terms properly obfuscated (40% weight)
- **Precision**: Only target terms obfuscated, no false positives (35% weight)  
- **Visual Integrity**: Layout and appearance preserved (25% weight)

### Storage

- **Local**: Storage on local file system (default)
- **S3**: AWS S3 support with key or IAM authentication

#### S3 Configuration

```python
from src.adapters.s3_storage_adapter import S3StorageAdapter
from src.application.pdf_obfuscation_app import PdfObfuscationApplication

# With explicit keys
s3_storage = S3StorageAdapter(
    bucket_name="my-bucket",
    aws_access_key_id="...",
    aws_secret_access_key="...",
    region_name="eu-west-1"
)

# Or with IAM/env authentication
s3_storage = S3StorageAdapter(bucket_name="my-bucket")

app = PdfObfuscationApplication(file_storage=s3_storage)
```

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Tests with coverage
uv run pytest --cov=src

# Specific tests
uv run pytest tests/unit/
uv run pytest tests/integration/
```

### Test structure

```
tests/
├── unit/                 # Unit tests by layer
│   ├── domain/          # Business entities and services tests
│   ├── ports/           # Interface tests
│   └── adapters/        # Adapter tests
├── integration/         # Integration tests
│   ├── test_api.py     # FastAPI tests
│   └── test_cli.py     # CLI interface tests
└── fixtures/            # Test data
    └── sample.pdf
```

## 🛠️ Development

### Adding a new PDF engine

1. Create an adapter implementing `PdfProcessorPort`
2. Register it in the application
3. Add corresponding tests

```python
# src/adapters/new_engine_adapter.py
from src.ports.pdf_processor_port import PdfProcessorPort

class NewEngineAdapter(PdfProcessorPort):
    def extract_text_occurrences(self, document, term):
        # Specific implementation
        pass
    
    def obfuscate_occurrences(self, document, occurrences):
        # Specific implementation
        pass
```

### Adding a new storage system

Same principle with `FileStoragePort`:

```python
# src/adapters/new_storage_adapter.py
from src.ports.file_storage_port import FileStoragePort

class NewStorageAdapter(FileStoragePort):
    def read_file(self, file_path):
        # Specific implementation
        pass
```

### Using Mistral AI OCR

For enhanced OCR accuracy, you can use the Mistral AI OCR evaluator:

```python
from src.adapters.mistral_text_extractor import MistralTextExtractor
from src.application.pdf_obfuscation_app import PdfObfuscationApplication

# Create Mistral evaluator
mistral_evaluator = MistralTextExtractor(
    file_storage=file_storage,
    mistral_api_key="your-api-key"  # or use MISTRAL_API_KEY env var
)

# Use in application
app = PdfObfuscationApplication(
    quality_evaluator=mistral_evaluator
)
```

**Test Mistral OCR:**
```bash
export MISTRAL_API_KEY="your-api-key"
./test_mistral_ocr.sh
```
