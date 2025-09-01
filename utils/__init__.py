# ────────────────────────────── utils/__init__.py ──────────────────────────────
"""
Medical AI Assistant - Utility Package

This package provides:
- API key rotation system for reliability
- Embedding client with fallback support
- Structured logging utilities
- Helper functions and utilities
"""

from .rotator import APIKeyRotator, robust_post_json
from .embeddings import EmbeddingClient, create_embedding_client
from .logger import get_logger

__all__ = [
    'APIKeyRotator',
    'robust_post_json',
    'EmbeddingClient',
    'create_embedding_client',
    'get_logger'
]

__version__ = "1.0.0"
