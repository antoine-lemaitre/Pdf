"""
Quality evaluation annotation schema for Mistral Document AI.
This schema defines the structured output format for evaluating obfuscation quality.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any


class QualityMetrics(BaseModel):
    """Quality metrics extracted from the document."""
    total_words: int = Field(..., description="Total number of words in the document")
    unique_words: int = Field(..., description="Number of unique words in the document")
    document_type: str = Field(..., description="Type of document (CV, invoice, contract, etc.)")
    language: str = Field(..., description="Primary language of the document")


class ObfuscationAnalysis(BaseModel):
    """Analysis of obfuscation quality."""
    preserved_words_count: int = Field(..., description="Number of words that were preserved after obfuscation")
    missing_words_count: int = Field(..., description="Number of words that disappeared after obfuscation")
    precision_score: float = Field(..., description="Precision score (0.0 to 1.0) based on preserved words")
    obfuscation_effectiveness: str = Field(..., description="Assessment of obfuscation effectiveness")


class DocumentQualityAnnotation(BaseModel):
    """Complete document quality evaluation annotation."""
    quality_metrics: QualityMetrics = Field(..., description="Basic quality metrics of the document")
    obfuscation_analysis: ObfuscationAnalysis = Field(..., description="Analysis of obfuscation quality")
    summary: str = Field(..., description="Overall summary of document quality and obfuscation effectiveness")
    confidence_score: float = Field(..., description="Confidence score of this evaluation (0.0 to 1.0)")

