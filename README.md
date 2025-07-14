# PDF Obfuscation Service

Un service d'obfuscation de documents PDF avec architecture hexagonale, supportant les modes CLI et API REST.

## 🏗️ Architecture

Ce projet suit une **architecture hexagonale (ports et adapters)** pour séparer clairement la logique métier des détails d'implémentation :

```
src/
├── domain/               # Cœur métier - Logique pure sans dépendances
│   ├── entities.py      # Entités métier (Document, Term, ObfuscationResult...)
│   ├── services.py      # Services métier purs 
│   └── exceptions.py    # Exceptions métier
├── ports/               # Interfaces - Contrats entre domaine et adapters
│   ├── pdf_processor_port.py    # Interface pour traitement PDF
│   └── file_storage_port.py     # Interface pour stockage de fichiers
├── use_cases/           # Orchestration - Cas d'usage métier
│   └── obfuscate_document.py
├── adapters/            # Implémentations - Détails techniques
│   ├── pymupdf_adapter.py       # Implémentation PyMuPDF
│   ├── local_storage_adapter.py # Stockage local
│   ├── s3_storage_adapter.py    # Stockage S3
│   └── fastapi_adapter.py       # Interface web REST
├── application/         # Coordination - Point d'entrée applicatif
│   └── pdf_obfuscation_app.py
└── cli.py              # Interface ligne de commande
```

### Avantages de cette architecture

- **Testabilité** : Chaque couche peut être testée indépendamment
- **Flexibilité** : Facile d'ajouter de nouveaux moteurs PDF ou systèmes de stockage
- **Maintenabilité** : Séparation claire des responsabilités
- **Évolutivité** : Logique métier protégée des changements techniques

## 🚀 Installation

### Prérequis

- Python 3.12+
- uv (gestionnaire de packages)

### Installation des dépendances

```bash
# Installer uv si nécessaire
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installer les dépendances
uv sync

# Installer les dépendances de développement
uv sync --extra dev
```

## 📋 Utilisation

Le service peut être utilisé en mode CLI ou serveur API.

### Mode CLI

```bash
# Obfusquer des termes dans un PDF (PyMuPDF par défaut)
python main.py document.pdf --terms "John Doe" "123-45-6789"

# Obfusquer des termes dans un PDF (PyMuPDF par défaut)
python main.py document.pdf --terms "John Doe" "123-45-6789"

# Spécifier un fichier de sortie
python main.py input.pdf --terms "confidentiel" --output output.pdf

# Valider un document
python main.py --validate document.pdf

# Afficher les moteurs disponibles
python main.py --engines

# Mode verbeux avec sortie JSON
python main.py document.pdf --terms "secret" --verbose --format json
```

### Mode Serveur API

```bash
# Démarrer le serveur
python main.py server

# Avec configuration personnalisée
python main.py server --host 0.0.0.0 --port 8080 --reload
```

### API REST

Une fois le serveur démarré, l'API est disponible sur `http://localhost:8000`

#### Documentation interactive
- Swagger UI : `http://localhost:8000/docs`
- ReDoc : `http://localhost:8000/redoc`

#### Endpoints principaux

```bash
# Santé du service
GET /health

# Moteurs disponibles
GET /engines

# Obfuscation via upload de fichier
POST /obfuscate
# Form-data: file (PDF), terms (string), engine (string)

# Obfuscation via JSON
POST /obfuscate-json
# JSON: {"source_path": "...", "terms": [...], "engine": "pymupdf"}

# Validation de document
POST /validate
# Form-data: file (PDF)

# Téléchargement de fichier obfusqué
GET /download/{file_path}
```

### Exemples d'utilisation de l'API

```bash
# Upload et obfuscation (PyMuPDF)
curl -X POST "http://localhost:8000/obfuscate" \
  -F "file=@document.pdf" \
  -F "terms=John Doe,123-45-6789" \
  -F "engine=pymupdf"

# Upload et obfuscation (PyMuPDF)
curl -X POST "http://localhost:8000/obfuscate" \
  -F "file=@document.pdf" \
  -F "terms=John Doe,123-45-6789" \
  -F "engine=pymupdf"

# Obfuscation via JSON (fichier local)
curl -X POST "http://localhost:8000/obfuscate-json" \
  -H "Content-Type: application/json" \
  -d '{
    "source_path": "/path/to/document.pdf",
    "terms": ["confidentiel", "secret"],
    "destination_path": "/path/to/output.pdf",
    "engine": "pymupdf"
  }'

# Validation
curl -X POST "http://localhost:8000/validate" \
  -F "file=@document.pdf"
```

## 🔧 Configuration

### Moteurs d'obfuscation

Actuellement supportés :
- **PyMuPDF** : Moteur principal, utilise des rectangles gris pour masquer le texte (licence AGPL)

### Stockage

- **Local** : Stockage sur le système de fichiers local (par défaut)
- **S3** : Support AWS S3 avec authentification par clés ou IAM

#### Configuration S3

```python
from src.adapters.s3_storage_adapter import S3StorageAdapter
from src.application.pdf_obfuscation_app import PdfObfuscationApplication

# Avec clés explicites
s3_storage = S3StorageAdapter(
    bucket_name="my-bucket",
    aws_access_key_id="...",
    aws_secret_access_key="...",
    region_name="eu-west-1"
)

# Ou avec authentification IAM/env
s3_storage = S3StorageAdapter(bucket_name="my-bucket")

app = PdfObfuscationApplication(file_storage=s3_storage)
```

## 🧪 Tests

```bash
# Lancer tous les tests
uv run pytest

# Tests avec couverture
uv run pytest --cov=src

# Tests spécifiques
uv run pytest tests/unit/
uv run pytest tests/integration/
```

### Structure des tests

```
tests/
├── unit/                 # Tests unitaires par couche
│   ├── domain/          # Tests des entités et services métier
│   ├── ports/           # Tests des interfaces
│   └── adapters/        # Tests des adapters
├── integration/         # Tests d'intégration
│   ├── test_api.py     # Tests de l'API FastAPI
│   └── test_cli.py     # Tests de l'interface CLI
└── fixtures/            # Données de test
    └── sample.pdf
```

## 🛠️ Développement

### Ajout d'un nouveau moteur PDF

1. Créer un adapter implémentant `PdfProcessorPort`
2. L'enregistrer dans l'application
3. Ajouter les tests correspondants

```python
# src/adapters/nouveau_moteur_adapter.py
from src.ports.pdf_processor_port import PdfProcessorPort

class NouveauMoteurAdapter(PdfProcessorPort):
    def extract_text_occurrences(self, document, term):
        # Implémentation spécifique
        pass
    
    def obfuscate_occurrences(self, document, occurrences):
        # Implémentation spécifique
        pass
```

### Ajout d'un nouveau système de stockage

Même principe avec `FileStoragePort` :

```python
# src/adapters/nouveau_storage_adapter.py
from src.ports.file_storage_port import FileStoragePort

class NouveauStorageAdapter(FileStoragePort):
    def read_file(self, file_path):
        # Implémentation spécifique
        pass
    
    def write_file(self, file_path, content):
        # Implémentation spécifique
        pass
    
    # ... autres méthodes
```

## 📊 Monitoring et Logs

Le service utilise le logging standard de Python. Niveau configurable via `--log-level` en mode serveur.

## 🚧 Limitations connues

- Seul PyMuPDF est actuellement supporté
- L'obfuscation utilise des rectangles de masquage (pas de remplacement de texte)
- Pas de support des PDF protégés par mot de passe

## 🗺️ Roadmap

- [ ] Support de moteurs PDF additionnels
- [ ] Obfuscation par remplacement de texte
- [ ] Support des PDF protégés
- [ ] Interface web complète
- [ ] Métriques et monitoring avancés
- [ ] Tests de performance et benchmarks

## 📝 Licence

[Spécifier la licence utilisée]

## 🤝 Contribution

Les contributions sont les bienvenues ! Merci de :

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Commiter les changements (`git commit -am 'Ajoute nouvelle fonctionnalité'`)
4. Pousser vers la branche (`git push origin feature/nouvelle-fonctionnalite`)
5. Ouvrir une Pull Request

## 📞 Support

Pour toute question ou problème, ouvrir une issue sur le projet.
