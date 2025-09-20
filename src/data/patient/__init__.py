# data/patient/__init__.py
"""
Patient management operations for MongoDB.
"""

from .operations import (
    get_patient_by_id,
    create_patient,
    update_patient_profile,
    search_patients,
)

__all__ = [
    'get_patient_by_id',
    'create_patient',
    'update_patient_profile',
    'search_patients',
]
