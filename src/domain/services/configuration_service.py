"""
Configuration service for PDF obfuscation.
Centralizes all configuration parameters and default values.
"""
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass(frozen=True)
class PathConfiguration:
    """Configuration for file paths."""
    input_directory: str
    output_directory: str
    default_output_suffix: str


@dataclass(frozen=True)
class EngineConfiguration:
    """Configuration for processing engines."""
    default_engine: str
    supported_engines: List[str]
    engine_timeout: int


@dataclass(frozen=True)
class QualityConfiguration:
    """Configuration for quality evaluation."""
    default_evaluator: str
    supported_evaluators: List[str]
    quality_threshold: float


class ConfigurationService:
    """Service for managing application configuration."""
    
    def __init__(self):
        """Initialize with default configuration."""
        self._path_config = self._create_path_configuration()
        self._engine_config = self._create_engine_configuration()
        self._quality_config = self._create_quality_configuration()
    
    def get_default_output_path(self, input_path: str) -> str:
        """
        Generate default output path for an input file.
        
        Args:
            input_path: Path to input file
            
        Returns:
            Default output path
        """
        input_path_obj = Path(input_path)
        
        # If input is in the configured input directory, use output directory
        if self._path_config.input_directory in str(input_path_obj):
            output_path = str(input_path_obj).replace(
                self._path_config.input_directory, 
                self._path_config.output_directory
            )
        else:
            # Otherwise, use same directory with suffix
            output_path = str(input_path_obj.parent / f"{input_path_obj.stem}{self._path_config.default_output_suffix}")
        
        return output_path
    
    def get_supported_engines(self) -> List[str]:
        """Get list of supported processing engines."""
        return self._engine_config.supported_engines.copy()
    
    def get_default_engine(self) -> str:
        """Get default processing engine."""
        return self._engine_config.default_engine
    
    def get_output_directory(self) -> str:
        """Get configured output directory."""
        return self._path_config.output_directory
    
    def get_input_directory(self) -> str:
        """Get configured input directory."""
        return self._path_config.input_directory
    
    def get_supported_evaluators(self) -> List[str]:
        """Get list of supported quality evaluators."""
        return self._quality_config.supported_evaluators.copy()
    
    def get_default_evaluator(self) -> str:
        """Get default quality evaluator."""
        return self._quality_config.default_evaluator
    
    def get_quality_threshold(self) -> float:
        """Get quality threshold for evaluation."""
        return self._quality_config.quality_threshold
    
    def get_engine_timeout(self) -> int:
        """Get timeout for engine operations."""
        return self._engine_config.engine_timeout
    
    def validate_engine(self, engine: str) -> bool:
        """
        Validate if an engine is supported.
        
        Args:
            engine: Engine name to validate
            
        Returns:
            True if engine is supported
        """
        return engine in self._engine_config.supported_engines
    
    def validate_evaluator(self, evaluator: str) -> bool:
        """
        Validate if an evaluator is supported.
        
        Args:
            evaluator: Evaluator name to validate
            
        Returns:
            True if evaluator is supported
        """
        return evaluator in self._quality_config.supported_evaluators
    
    def _create_path_configuration(self) -> PathConfiguration:
        """Create path configuration with defaults and environment overrides."""
        return PathConfiguration(
            input_directory=os.getenv("PDF_INPUT_DIR", "data/input"),
            output_directory=os.getenv("PDF_OUTPUT_DIR", "data/output"),
            default_output_suffix="_obfuscated.pdf"
        )
    
    def _create_engine_configuration(self) -> EngineConfiguration:
        """Create engine configuration with defaults and environment overrides."""
        return EngineConfiguration(
            default_engine=os.getenv("PDF_DEFAULT_ENGINE", "pymupdf"),
            supported_engines=["pymupdf", "pypdfium2", "pdfplumber"],
            engine_timeout=int(os.getenv("PDF_ENGINE_TIMEOUT", "300"))
        )
    
    def _create_quality_configuration(self) -> QualityConfiguration:
        """Create quality configuration with defaults and environment overrides."""
        return QualityConfiguration(
            default_evaluator=os.getenv("PDF_DEFAULT_EVALUATOR", "tesseract"),
            supported_evaluators=["tesseract", "mistral"],
            quality_threshold=float(os.getenv("PDF_QUALITY_THRESHOLD", "0.8"))
        )
