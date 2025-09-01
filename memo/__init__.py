# ────────────────────────────── memo/__init__.py ──────────────────────────────
"""
Medical AI Assistant - Memory and History Management Package

This package provides:
- Enhanced LRU memory system for user data and chat sessions
- Medical history manager for context-aware conversations
- User profile and session management
- Medical context storage and retrieval
"""

from .memory import MemoryLRU, ChatSession, UserProfile
from .history import MedicalHistoryManager, summarize_qa_with_nvidia, files_relevance

__all__ = [
    'MemoryLRU',
    'ChatSession', 
    'UserProfile',
    'MedicalHistoryManager',
    'summarize_qa_with_nvidia',
    'files_relevance'
]

__version__ = "1.0.0"
