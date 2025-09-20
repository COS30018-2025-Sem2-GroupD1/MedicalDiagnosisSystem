# data/__init__.py
"""
Data layer for MongoDB operations.
Organized into specialized modules for different data types.
"""

from .connection import get_database, get_collection, close_connection
from .session import *
from .user import *
from .message import *
from .patient import *
from .medical import *
from .utils import create_index, backup_collection

__all__ = [
    # Connection
    'get_database',
    'get_collection', 
    'close_connection',
    # Session functions
    'create_chat_session',
    'get_user_sessions',
    'ensure_session',
    'list_patient_sessions',
    'delete_session',
    'delete_session_messages',
    'delete_old_sessions',
    # User functions
    'create_account',
    'update_account',
    'get_account_frame',
    'create_doctor',
    'get_doctor_by_name',
    'search_doctors',
    'get_all_doctors',
    # Message functions
    'add_message',
    'get_session_messages',
    'save_chat_message',
    'list_session_messages',
    # Patient functions
    'get_patient_by_id',
    'create_patient',
    'update_patient_profile',
    'search_patients',
    # Medical functions
    'create_medical_record',
    'get_user_medical_records',
    'save_memory_summary',
    'get_recent_memory_summaries',
    'search_memory_summaries_semantic',
    # Utility functions
    'create_index',
    'backup_collection',
]
