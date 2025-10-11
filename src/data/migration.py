# src/data/migration.py
"""
Database Migration Module

This module provides functions to fix existing database records that have 
missing or invalid required fields to ensure they conform to current Pydantic model requirements.
"""

from datetime import datetime, timezone
from typing import Dict, Any

from bson import ObjectId
from pymongo.errors import ConnectionFailure, PyMongoError

from src.data.connection import get_collection, Collections
from src.models.account import Account
from src.models.patient import Patient
from src.utils.logger import logger

# Valid roles for accounts
VALID_ROLES = [
    "Doctor",
    "Healthcare Prof", 
    "Nurse",
    "Caregiver",
    "Physician",
    "Medical Student",
    "Other"
]

def fix_account_records() -> Dict[str, int]:
    """Fix account records with missing or invalid required fields."""
    logger().info("🔧 Starting Account records migration...")
    
    collection = get_collection(Collections.ACCOUNT)
    now = datetime.now(timezone.utc)
    
    stats = {
        'total_checked': 0,
        'fixed': 0,
        'errors': 0
    }
    
    try:
        # Find all accounts
        cursor = collection.find({})
        
        for doc in cursor:
            stats['total_checked'] += 1
            doc_id = doc['_id']
            
            try:
                # Check what needs to be fixed
                updates = {}
                needs_fix = False
                
                # Fix missing or None role
                if not doc.get('role') or doc.get('role') is None:
                    updates['role'] = 'Other'  # Default role
                    needs_fix = True
                    logger().info(f"  📝 Account {doc_id}: Setting role to 'Other' (was: {doc.get('role')})")
                
                # Fix missing or None name
                if not doc.get('name') or doc.get('name') is None:
                    updates['name'] = f"User {str(doc_id)[:8]}"  # Generate a name
                    needs_fix = True
                    logger().info(f"  📝 Account {doc_id}: Setting name to '{updates['name']}' (was: {doc.get('name')})")
                
                # Fix missing timestamps
                if not doc.get('created_at'):
                    updates['created_at'] = now
                    needs_fix = True
                    logger().info(f"  📝 Account {doc_id}: Setting created_at to {now}")
                
                if not doc.get('updated_at'):
                    updates['updated_at'] = now
                    needs_fix = True
                    logger().info(f"  📝 Account {doc_id}: Setting updated_at to {now}")
                
                # Apply updates if needed
                if needs_fix:
                    collection.update_one(
                        {"_id": doc_id},
                        {"$set": updates}
                    )
                    stats['fixed'] += 1
                
                # Validate the record can be parsed by Pydantic
                updated_doc = collection.find_one({"_id": doc_id})
                Account.model_validate(updated_doc)
                
            except Exception as e:
                stats['errors'] += 1
                logger().error(f"  ❌ Error fixing account {doc_id}: {e}")
                
    except (ConnectionFailure, PyMongoError) as e:
        logger().error(f"❌ Database error while fixing accounts: {e}")
        raise
    
    logger().info(f"✅ Account migration completed: {stats['fixed']} records fixed, {stats['errors']} errors")
    return stats

def fix_patient_records() -> Dict[str, int]:
    """Fix patient records with missing or invalid required fields."""
    logger().info("🔧 Starting Patient records migration...")
    
    collection = get_collection(Collections.PATIENT)
    now = datetime.now(timezone.utc)
    
    stats = {
        'total_checked': 0,
        'fixed': 0,
        'errors': 0
    }
    
    try:
        # Find all patients
        cursor = collection.find({})
        
        for doc in cursor:
            stats['total_checked'] += 1
            doc_id = doc['_id']
            
            try:
                # Check what needs to be fixed
                updates = {}
                needs_fix = False
                
                # Fix missing or None name
                if not doc.get('name') or doc.get('name') is None:
                    updates['name'] = f"Patient {str(doc_id)[:8]}"  # Generate a name
                    needs_fix = True
                    logger().info(f"  📝 Patient {doc_id}: Setting name to '{updates['name']}' (was: {doc.get('name')})")
                
                # Fix missing or None age
                if not doc.get('age') or doc.get('age') is None:
                    updates['age'] = 30  # Default age
                    needs_fix = True
                    logger().info(f"  📝 Patient {doc_id}: Setting age to 30 (was: {doc.get('age')})")
                
                # Fix missing or None sex
                if not doc.get('sex') or doc.get('sex') is None:
                    updates['sex'] = 'Other'  # Default sex
                    needs_fix = True
                    logger().info(f"  📝 Patient {doc_id}: Setting sex to 'Other' (was: {doc.get('sex')})")
                
                # Fix missing or None ethnicity
                if not doc.get('ethnicity') or doc.get('ethnicity') is None:
                    updates['ethnicity'] = 'Not Specified'  # Default ethnicity
                    needs_fix = True
                    logger().info(f"  📝 Patient {doc_id}: Setting ethnicity to 'Not Specified' (was: {doc.get('ethnicity')})")
                
                # Fix missing timestamps
                if not doc.get('created_at'):
                    updates['created_at'] = now
                    needs_fix = True
                    logger().info(f"  📝 Patient {doc_id}: Setting created_at to {now}")
                
                if not doc.get('updated_at'):
                    updates['updated_at'] = now
                    needs_fix = True
                    logger().info(f"  📝 Patient {doc_id}: Setting updated_at to {now}")
                
                # Apply updates if needed
                if needs_fix:
                    collection.update_one(
                        {"_id": doc_id},
                        {"$set": updates}
                    )
                    stats['fixed'] += 1
                
                # Validate the record can be parsed by Pydantic
                updated_doc = collection.find_one({"_id": doc_id})
                Patient.model_validate(updated_doc)
                
            except Exception as e:
                stats['errors'] += 1
                logger().error(f"  ❌ Error fixing patient {doc_id}: {e}")
                
    except (ConnectionFailure, PyMongoError) as e:
        logger().error(f"❌ Database error while fixing patients: {e}")
        raise
    
    logger().info(f"✅ Patient migration completed: {stats['fixed']} records fixed, {stats['errors']} errors")
    return stats

def run_database_migration() -> Dict[str, Any]:
    """Run the complete database migration to fix all records."""
    logger().info("🚀 Starting Database Migration")
    logger().info("=" * 50)
    
    try:
        # Fix account records
        account_stats = fix_account_records()
        
        logger().info("=" * 50)
        
        # Fix patient records  
        patient_stats = fix_patient_records()
        
        logger().info("=" * 50)
        logger().info("📊 MIGRATION SUMMARY")
        logger().info("=" * 50)
        
        logger().info(f"📋 Accounts:")
        logger().info(f"  - Total checked: {account_stats['total_checked']}")
        logger().info(f"  - Fixed: {account_stats['fixed']}")
        logger().info(f"  - Errors: {account_stats['errors']}")
        
        logger().info(f"👥 Patients:")
        logger().info(f"  - Total checked: {patient_stats['total_checked']}")
        logger().info(f"  - Fixed: {patient_stats['fixed']}")
        logger().info(f"  - Errors: {patient_stats['errors']}")
        
        total_fixed = account_stats['fixed'] + patient_stats['fixed']
        total_errors = account_stats['errors'] + patient_stats['errors']
        
        logger().info(f"✅ Total records fixed: {total_fixed}")
        if total_errors > 0:
            logger().info(f"⚠️  Total errors: {total_errors}")
        
        logger().info("🎉 Database migration completed successfully!")
        
        return {
            'account_stats': account_stats,
            'patient_stats': patient_stats,
            'total_fixed': total_fixed,
            'total_errors': total_errors,
            'success': True
        }
        
    except Exception as e:
        logger().error(f"❌ Migration failed with error: {e}")
        return {
            'success': False,
            'error': str(e)
        }
