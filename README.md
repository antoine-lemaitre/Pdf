# PDF Obfuscation Service

A PDF document obfuscation service with hexagonal architecture, supporting CLI and REST API modes.

## 🏗️ Architecture

This project follows a **hexagonal architecture (ports and adapters)** to clearly separate business logic from implementation details:

```
src/
├── domain/               # Business core - Pure logic without dependencies
│   ├── entities.py      # Business entities (Document, Term, ObfuscationResult...)
│   ├── services.py      # Pure business services 
│   └── exceptions.py    # Business exceptions
├── ports/               # Interfaces - Contracts between domain and adapters
│   ├── pdf_processor_port.py    # Interface for PDF processing
│   └── file_storage_port.py     # Interface for file storage
├── use_cases/           # Orchestration - Business use cases
│   └── obfuscate_document.py
├── adapters/            # Implementations - Technical details
│   ├── pymupdf_adapter.py       # PyMuPDF implementation
│   ├── local_storage_adapter.py # Local storage
│   ├── s3_storage_adapter.py    # S3 storage
│   └── fastapi_adapter.py       # REST web interface
├── application/         # Coordination - Application entry point
│   └── pdf_obfuscation_app.py
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
uv run main.py document.pdf --terms "John Doe" "123-45-6789"

# Obfuscate terms in a PDF (PyMuPDF by default)
uv run main.py document.pdf --terms "John Doe" "123-45-6789"

# Specify an output file
uv run main.py input.pdf --terms "confidential" --output output.pdf

# Validate a document
uv run main.py --validate document.pdf

# Show available engines
uv run main.py --engines

# Verbose mode with JSON output
uv run main.py document.pdf --terms "secret" --verbose --format json
```

### API Server Mode

```bash
# Start the server
uv run main.py server

# With custom configuration
uv run main.py server --host 0.0.0.0 --port 8080 --reload
```

### REST API

Once the server is started, the API is available at `http://localhost:8000`

#### Interactive documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

#### Main endpoints

```bash
# Service health
GET /health

# Available engines
GET /engines

# Obfuscation via file upload
POST /obfuscate
# Form-data: file (PDF), terms (string), engine (string)

# Obfuscation via JSON
POST /obfuscate-json
# JSON: {"source_path": "...", "terms": [...], "engine": "pymupdf"}

# Document validation
POST /validate
# Form-data: file (PDF)

# Download obfuscated file
GET /download/{file_path}
```

### API usage examples

```bash
# Upload and obfuscation (PyMuPDF)
curl -X POST "http://localhost:8000/obfuscate" \
  -F "file=@document.pdf" \
  -F "terms=John Doe,123-45-6789" \
  -F "engine=pymupdf"

# Obfuscation via JSON (local file)
curl -X POST "http://localhost:8000/obfuscate-json" \
  -H "Content-Type: application/json" \
  -d '{
    "source_path": "/path/to/document.pdf",
    "terms": ["confidential", "secret"],
    "destination_path": "/path/to/output.pdf",
    "engine": "pymupdf"
  }'

# Validation
curl -X POST "http://localhost:8000/validate" \
  -F "file=@document.pdf"
```

## 🔧 Configuration

### Obfuscation engines

Currently supported:
- **PyMuPDF**: Main engine, uses gray rectangles to mask text (AGPL license)

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
