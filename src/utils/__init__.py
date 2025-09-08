# ────────────────────────────── utils/__init__.py ──────────────────────────────
"""
Medical AI Assistant - Utility Package

This package provides:
- API key rotation system for reliability
- Embedding client with fallback support
- Structured logging utilities
- Helper functions and utilities
"""

from .embeddings import EmbeddingClient
from .logger import logger
from .rotator import APIKeyRotator, robust_post_json

__all__ = [
	'APIKeyRotator',
	'robust_post_json',
	'EmbeddingClient',
	'logger'
]

__version__ = "1.0.0"
