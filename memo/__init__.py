# ────────────────────────────── memo/__init__.py ──────────────────────────────
"""
Medical AI Assistant - Memory and History Management Package

This package provides:
- Enhanced LRU memory system for user data and chat sessions
- Medical history manager for context-aware conversations
- User profile and session management
- Medical context storage and retrieval
"""

from .history import (MedicalHistoryManager, files_relevance,
					  summarize_qa_with_nvidia)
from .memory import ChatSession, MemoryLRU, UserProfile

__all__ = [
	'MemoryLRU',
	'ChatSession',
	'UserProfile',
	'MedicalHistoryManager',
	'summarize_qa_with_nvidia',
	'files_relevance'
]

__version__ = "1.0.0"
