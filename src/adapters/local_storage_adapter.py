import os
from pathlib import Path
from src.ports.file_storage_port import FileStoragePort
from src.domain.exceptions import FileStorageError


class LocalStorageAdapter(FileStoragePort):
    """Adapter pour le stockage de fichiers local."""
    
    def __init__(self, base_path: str = "."):
        """
        Initialise l'adapter de stockage local.
        
        Args:
            base_path: Répertoire de base pour les opérations de fichiers
        """
        self.base_path = Path(base_path).resolve()
    
    def read_file(self, file_path: str) -> bytes:
        """
        Lit un fichier depuis le système de fichiers local.
        
        Args:
            file_path: Chemin vers le fichier
            
        Returns:
            bytes: Contenu du fichier
            
        Raises:
            FileStorageError: En cas d'erreur de lecture
        """
        try:
            file_path = self._resolve_path(file_path)
            
            if not file_path.exists():
                raise FileStorageError(f"Le fichier {file_path} n'existe pas")
            
            if not file_path.is_file():
                raise FileStorageError(f"{file_path} n'est pas un fichier")
            
            with open(file_path, 'rb') as f:
                return f.read()
                
        except FileStorageError:
            raise
        except Exception as e:
            raise FileStorageError(f"Erreur lors de la lecture du fichier {file_path}: {str(e)}")
    
    def write_file(self, file_path: str, content: bytes) -> None:
        """
        Écrit un fichier dans le système de fichiers local.
        
        Args:
            file_path: Chemin de destination
            content: Contenu à écrire
            
        Raises:
            FileStorageError: En cas d'erreur d'écriture
        """
        try:
            file_path = self._resolve_path(file_path)
            
            # Créer les répertoires parents si nécessaire
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(content)
                
        except Exception as e:
            raise FileStorageError(f"Error writing file {file_path}: {str(e)}")
    
    def file_exists(self, file_path: str) -> bool:
        """
        Vérifie si un fichier existe.
        
        Args:
            file_path: Chemin vers le fichier
            
        Returns:
            bool: True si le fichier existe
        """
        try:
            file_path = self._resolve_path(file_path)
            return file_path.exists() and file_path.is_file()
        except Exception:
            return False
    
    def delete_file(self, file_path: str) -> None:
        """
        Supprime un fichier.
        
        Args:
            file_path: Chemin vers le fichier à supprimer
            
        Raises:
            FileStorageError: En cas d'erreur de suppression
        """
        try:
            file_path = self._resolve_path(file_path)
            
            if file_path.exists():
                file_path.unlink()
                
        except Exception as e:
            raise FileStorageError(f"Erreur lors de la suppression du fichier {file_path}: {str(e)}")
    
    def _resolve_path(self, file_path: str) -> Path:
        """
        Résout un chemin relatif par rapport au répertoire de base.
        
        Args:
            file_path: Chemin du fichier
            
        Returns:
            Path: Chemin résolu
        """
        path = Path(file_path)
        
        if path.is_absolute():
            return path
        else:
            return self.base_path / path 