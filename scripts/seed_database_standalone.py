#!/usr/bin/env python3
# scripts/seed_database_standalone.py
"""
Standalone database seeder script for populating MongoDB with sample data.
This version works with Python 3.9+ and doesn't require importing the full project.

Usage:
    export MONGO_USER="mongodb://localhost:27017/"
    python3 scripts/seed_database_standalone.py
"""

import os
import sys
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import json

try:
    from pymongo import MongoClient, ASCENDING, DESCENDING
    from bson import ObjectId
    from bson.errors import InvalidId
except ImportError as e:
    print(f"❌ Error: Required packages not installed. Please install pymongo: pip install pymongo")
    sys.exit(1)


# Sample data definitions
DOCTORS = [
    {"name": "Dr. Sarah Johnson", "role": "Doctor", "specialty": "Cardiology"},
    {"name": "Dr. Michael Chen", "role": "Physician", "specialty": "Internal Medicine"},
    {"name": "Dr. Emily Rodriguez", "role": "Doctor", "specialty": "Pediatrics"},
    {"name": "Dr. James Wilson", "role": "Doctor", "specialty": "Orthopedics"},
    {"name": "Dr. Lisa Anderson", "role": "Physician", "specialty": "Dermatology"},
]

PATIENTS = [
    {
        "name": "John Smith",
        "age": 45,
        "sex": "Male",
        "ethnicity": "Caucasian",
        "address": "123 Main St, Melbourne VIC 3000",
        "phone": "+61 412 345 678",
        "email": "john.smith@email.com",
        "medications": ["Aspirin 100mg", "Lisinopril 10mg"],
        "past_assessment_summary": "Patient has a history of hypertension and managed with medication. No known allergies."
    },
    {
        "name": "Maria Garcia",
        "age": 32,
        "sex": "Female",
        "ethnicity": "Hispanic",
        "address": "456 Oak Ave, Sydney NSW 2000",
        "phone": "+61 423 456 789",
        "email": "maria.garcia@email.com",
        "medications": ["Metformin 500mg", "Metoprolol 25mg"],
        "past_assessment_summary": "Type 2 diabetes diagnosed in 2020. Currently managing with diet and medication."
    },
    {
        "name": "David Kim",
        "age": 28,
        "sex": "Male",
        "ethnicity": "Asian",
        "address": "789 Pine Rd, Brisbane QLD 4000",
        "phone": "+61 434 567 890",
        "email": "david.kim@email.com",
        "medications": ["Ibuprofen 400mg"],
        "past_assessment_summary": "No significant medical history. Occasional sports injuries."
    },
    {
        "name": "Sarah Williams",
        "age": 55,
        "sex": "Female",
        "ethnicity": "African American",
        "address": "321 Elm St, Perth WA 6000",
        "phone": "+61 445 678 901",
        "email": "sarah.williams@email.com",
        "medications": ["Levothyroxine 75mcg", "Calcium 1000mg"],
        "past_assessment_summary": "Hypothyroidism diagnosed 5 years ago. Regular monitoring required."
    },
    {
        "name": "Ahmed Hassan",
        "age": 38,
        "sex": "Male",
        "ethnicity": "Middle Eastern",
        "address": "654 Maple Dr, Adelaide SA 5000",
        "phone": "+61 456 789 012",
        "email": "ahmed.hassan@email.com",
        "medications": ["Atorvastatin 20mg"],
        "past_assessment_summary": "Family history of heart disease. Managing cholesterol levels."
    },
    {
        "name": "Emma Thompson",
        "age": 25,
        "sex": "Female",
        "ethnicity": "Caucasian",
        "address": "987 Cedar Ln, Canberra ACT 2600",
        "phone": "+61 467 890 123",
        "email": "emma.thompson@email.com",
        "medications": None,
        "past_assessment_summary": "Healthy individual with no chronic conditions."
    },
    {
        "name": "Robert Brown",
        "age": 62,
        "sex": "Male",
        "ethnicity": "Caucasian",
        "address": "147 Birch Way, Hobart TAS 7000",
        "phone": "+61 478 901 234",
        "email": "robert.brown@email.com",
        "medications": ["Warfarin 5mg", "Amlodipine 5mg"],
        "past_assessment_summary": "History of atrial fibrillation. On anticoagulation therapy."
    },
    {
        "name": "Jennifer Lee",
        "age": 35,
        "sex": "Female",
        "ethnicity": "Asian",
        "address": "258 Spruce Ct, Darwin NT 0800",
        "phone": "+61 489 012 345",
        "email": "jennifer.lee@email.com",
        "medications": ["Sertraline 50mg"],
        "past_assessment_summary": "Managing anxiety and depression with medication and therapy."
    },
]

# Sample EMR entries
SAMPLE_EMR_DATA = [
    {
        "original_message": "Patient presents with chest pain and shortness of breath. Blood pressure 150/95, heart rate 88 bpm. Patient reports pain radiating to left arm. ECG shows no acute changes. Prescribed Aspirin 100mg daily and referred for cardiac evaluation.",
        "diagnosis": ["Chest pain", "Hypertension"],
        "symptoms": ["Chest pain", "Shortness of breath", "Pain radiating to left arm"],
        "medications": [
            {"name": "Aspirin", "dosage": "100mg", "frequency": "Daily", "duration": "Ongoing"}
        ],
        "vital_signs": {
            "blood_pressure": "150/95",
            "heart_rate": "88 bpm"
        },
        "lab_results": [],
        "procedures": ["ECG"],
        "notes": "ECG shows no acute changes. Referred for cardiac evaluation.",
        "confidence_score": 0.92
    },
    {
        "original_message": "Follow-up visit for diabetes management. HbA1c is 7.2%, fasting glucose 135 mg/dL. Patient reports good adherence to diet. Blood pressure well controlled at 120/80. Continuing current Metformin dosage.",
        "diagnosis": ["Type 2 Diabetes"],
        "symptoms": [],
        "medications": [
            {"name": "Metformin", "dosage": "500mg", "frequency": "Twice daily", "duration": "Ongoing"}
        ],
        "vital_signs": {
            "blood_pressure": "120/80",
            "heart_rate": "72 bpm"
        },
        "lab_results": [
            {"test_name": "HbA1c", "value": "7.2%", "unit": "%", "reference_range": "<7%"},
            {"test_name": "Fasting Glucose", "value": "135", "unit": "mg/dL", "reference_range": "70-100 mg/dL"}
        ],
        "procedures": [],
        "notes": "Patient reports good adherence to diet. Blood pressure well controlled.",
        "confidence_score": 0.88
    },
    {
        "original_message": "Patient complains of right knee pain after running. Examination shows swelling and limited range of motion. X-ray ordered shows no fracture. Prescribed Ibuprofen 400mg three times daily for 5 days and recommended rest.",
        "diagnosis": ["Knee injury", "Sports injury"],
        "symptoms": ["Right knee pain", "Swelling", "Limited range of motion"],
        "medications": [
            {"name": "Ibuprofen", "dosage": "400mg", "frequency": "Three times daily", "duration": "5 days"}
        ],
        "vital_signs": {},
        "lab_results": [],
        "procedures": ["X-ray right knee"],
        "notes": "X-ray shows no fracture. Recommended rest and NSAID therapy.",
        "confidence_score": 0.85
    },
    {
        "original_message": "Routine thyroid function check. TSH is 2.5 mIU/L (normal range). Patient feels well. Continue current Levothyroxine dosage. Next check in 6 months.",
        "diagnosis": ["Hypothyroidism"],
        "symptoms": [],
        "medications": [
            {"name": "Levothyroxine", "dosage": "75mcg", "frequency": "Daily", "duration": "Ongoing"}
        ],
        "vital_signs": {},
        "lab_results": [
            {"test_name": "TSH", "value": "2.5", "unit": "mIU/L", "reference_range": "0.5-4.5 mIU/L"}
        ],
        "procedures": [],
        "notes": "TSH within normal range. Patient feels well. Continue current medication.",
        "confidence_score": 0.90
    },
    {
        "original_message": "Annual cholesterol screening. Total cholesterol 220 mg/dL, LDL 145 mg/dL, HDL 55 mg/dL, Triglycerides 180 mg/dL. Patient on Atorvastatin 20mg. Continue current medication and recommend lifestyle modifications.",
        "diagnosis": ["Hypercholesterolemia"],
        "symptoms": [],
        "medications": [
            {"name": "Atorvastatin", "dosage": "20mg", "frequency": "Daily", "duration": "Ongoing"}
        ],
        "vital_signs": {},
        "lab_results": [
            {"test_name": "Total Cholesterol", "value": "220", "unit": "mg/dL", "reference_range": "<200 mg/dL"},
            {"test_name": "LDL", "value": "145", "unit": "mg/dL", "reference_range": "<100 mg/dL"},
            {"test_name": "HDL", "value": "55", "unit": "mg/dL", "reference_range": ">40 mg/dL"},
            {"test_name": "Triglycerides", "value": "180", "unit": "mg/dL", "reference_range": "<150 mg/dL"}
        ],
        "procedures": [],
        "notes": "Continue current medication and recommend lifestyle modifications.",
        "confidence_score": 0.87
    },
    {
        "original_message": "Annual wellness exam. Patient in good health. Blood pressure 118/75, heart rate 68 bpm, temperature 98.6°F. No complaints. Recommended routine vaccinations are up to date.",
        "diagnosis": [],
        "symptoms": [],
        "medications": [],
        "vital_signs": {
            "blood_pressure": "118/75",
            "heart_rate": "68 bpm",
            "temperature": "98.6°F"
        },
        "lab_results": [],
        "procedures": [],
        "notes": "Patient in good health. No complaints. Routine vaccinations up to date.",
        "confidence_score": 0.91
    },
    {
        "original_message": "Warfarin management appointment. INR is 2.3 (target range 2-3). Patient stable on current Warfarin 5mg daily dose. Blood pressure 130/85. Continue current anticoagulation therapy. Next INR check in 4 weeks.",
        "diagnosis": ["Atrial Fibrillation"],
        "symptoms": [],
        "medications": [
            {"name": "Warfarin", "dosage": "5mg", "frequency": "Daily", "duration": "Ongoing"}
        ],
        "vital_signs": {
            "blood_pressure": "130/85",
            "heart_rate": "75 bpm"
        },
        "lab_results": [
            {"test_name": "INR", "value": "2.3", "unit": "", "reference_range": "2-3"}
        ],
        "procedures": [],
        "notes": "INR within target range. Patient stable. Continue current therapy.",
        "confidence_score": 0.93
    },
    {
        "original_message": "Mental health follow-up visit. Patient reports improved mood and better sleep. Anxiety symptoms well controlled. Continue Sertraline 50mg daily. Next appointment in 3 months.",
        "diagnosis": ["Anxiety", "Depression"],
        "symptoms": [],
        "medications": [
            {"name": "Sertraline", "dosage": "50mg", "frequency": "Daily", "duration": "Ongoing"}
        ],
        "vital_signs": {},
        "lab_results": [],
        "procedures": [],
        "notes": "Patient reports improved mood and better sleep. Anxiety symptoms well controlled.",
        "confidence_score": 0.86
    },
]


def generate_embeddings(dimension: int = 768) -> List[float]:
    """Generate dummy embeddings for EMR entries."""
    import random
    random.seed(42)  # For reproducibility
    embeddings = [random.uniform(-0.1, 0.1) for _ in range(dimension)]
    magnitude = sum(x*x for x in embeddings) ** 0.5
    if magnitude > 0:
        embeddings = [x / magnitude for x in embeddings]
    return embeddings


def seed_doctors(db) -> List[str]:
    """Seed the database with doctor accounts."""
    print("Seeding doctor accounts...")
    collection = db["accounts"]
    doctor_ids = []
    
    for doctor_data in DOCTORS:
        try:
            now = datetime.now(timezone.utc)
            doc = {
                "name": doctor_data["name"],
                "role": doctor_data["role"],
                "specialty": doctor_data.get("specialty"),
                "created_at": now,
                "updated_at": now,
                "last_seen": now
            }
            result = collection.insert_one(doc)
            doctor_ids.append(str(result.inserted_id))
            print(f"  ✓ Created doctor: {doctor_data['name']} (ID: {result.inserted_id})")
        except Exception as e:
            print(f"  ✗ Failed to create doctor {doctor_data['name']}: {e}")
    
    print(f"Successfully created {len(doctor_ids)} doctor accounts\n")
    return doctor_ids


def seed_patients(db, doctor_ids: List[str]) -> List[str]:
    """Seed the database with patient accounts."""
    print("Seeding patient accounts...")
    collection = db["patients"]
    patient_ids = []
    
    for i, patient_data in enumerate(PATIENTS):
        try:
            # Assign patients to doctors in round-robin fashion
            assigned_doctor_id = doctor_ids[i % len(doctor_ids)] if doctor_ids else None
            
            now = datetime.now(timezone.utc)
            doc = {
                "name": patient_data["name"],
                "age": patient_data["age"],
                "sex": patient_data["sex"],
                "ethnicity": patient_data["ethnicity"],
                "created_at": now,
                "updated_at": now
            }
            
            # Add optional fields
            if patient_data.get("address"):
                doc["address"] = patient_data["address"]
            if patient_data.get("phone"):
                doc["phone"] = patient_data["phone"]
            if patient_data.get("email"):
                doc["email"] = patient_data["email"]
            if patient_data.get("medications"):
                doc["medications"] = patient_data["medications"]
            if patient_data.get("past_assessment_summary"):
                doc["past_assessment_summary"] = patient_data["past_assessment_summary"]
            if assigned_doctor_id:
                doc["assigned_doctor_id"] = ObjectId(assigned_doctor_id)
            
            result = collection.insert_one(doc)
            patient_ids.append(str(result.inserted_id))
            print(f"  ✓ Created patient: {patient_data['name']} (ID: {result.inserted_id})")
        except Exception as e:
            print(f"  ✗ Failed to create patient {patient_data['name']}: {e}")
    
    print(f"Successfully created {len(patient_ids)} patient accounts\n")
    return patient_ids


def seed_emrs(db, patient_ids: List[str], doctor_ids: List[str]) -> int:
    """Seed the database with EMR entries for patients."""
    print("Seeding EMR entries...")
    collection = db["emr"]
    emr_count = 0
    
    # Create indexes if they don't exist
    try:
        collection.create_index("patient_id")
        collection.create_index("doctor_id")
        collection.create_index("session_id")
        collection.create_index("message_id")
        collection.create_index([("patient_id", ASCENDING), ("created_at", DESCENDING)])
    except Exception:
        pass  # Indexes might already exist
    
    for i, patient_id in enumerate(patient_ids):
        if i < len(SAMPLE_EMR_DATA):
            emr_data = SAMPLE_EMR_DATA[i]
            doctor_id = doctor_ids[i % len(doctor_ids)] if doctor_ids else doctor_ids[0]
            
            try:
                # Generate unique IDs for message and session
                message_id = str(ObjectId())
                session_id = str(ObjectId())
                
                # Build extracted_data
                extracted_data = {
                    "diagnosis": emr_data["diagnosis"],
                    "symptoms": emr_data["symptoms"],
                    "medications": emr_data["medications"],
                    "lab_results": emr_data["lab_results"],
                    "procedures": emr_data["procedures"],
                    "notes": emr_data.get("notes")
                }
                # Only include vital_signs if it exists and is not empty
                if emr_data.get("vital_signs"):
                    extracted_data["vital_signs"] = emr_data["vital_signs"]
                
                # Generate embeddings
                embeddings = generate_embeddings()
                
                now = datetime.now(timezone.utc)
                doc = {
                    "patient_id": patient_id,
                    "doctor_id": doctor_id,
                    "message_id": message_id,
                    "session_id": session_id,
                    "original_message": emr_data["original_message"],
                    "extracted_data": extracted_data,
                    "embeddings": embeddings,
                    "confidence_score": emr_data["confidence_score"],
                    "created_at": now,
                    "updated_at": now
                }
                
                result = collection.insert_one(doc)
                emr_count += 1
                print(f"  ✓ Created EMR entry for patient {patient_id} (EMR ID: {result.inserted_id})")
                
            except Exception as e:
                print(f"  ✗ Failed to create EMR for patient {patient_id}: {e}")
    
    print(f"Successfully created {emr_count} EMR entries\n")
    return emr_count


def main():
    """Main function to run the seeder."""
    print("=" * 60)
    print("Medical Diagnosis System - Database Seeder (Standalone)")
    print("=" * 60)
    
    # Check for MongoDB connection string
    mongo_user = os.getenv("MONGO_USER")
    if not mongo_user:
        print("\n❌ Error: MONGO_USER environment variable not found!")
        print("\nPlease set the MONGO_USER environment variable:")
        print("  export MONGO_USER='mongodb://localhost:27017/'")
        print("\nFor remote MongoDB:")
        print("  export MONGO_USER='mongodb://host:port/'")
        sys.exit(1)
    
    print(f"\n✓ MongoDB connection string found")
    print(f"  Connection: {mongo_user.split('@')[-1] if '@' in mongo_user else mongo_user}")
    
    try:
        # Connect to MongoDB
        print("\nConnecting to MongoDB...")
        client = MongoClient(mongo_user, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        print("✓ Connected to MongoDB successfully")
        
        # Get database
        db_name = "medicaldiagnosissystem"
        db = client[db_name]
        print(f"✓ Using database: {db_name}\n")
        
        # Seed data
        print("-" * 60)
        print("Step 1: Creating doctor accounts...")
        print("-" * 60)
        doctor_ids = seed_doctors(db)
        
        print("-" * 60)
        print("Step 2: Creating patient accounts...")
        print("-" * 60)
        patient_ids = seed_patients(db, doctor_ids)
        
        print("-" * 60)
        print("Step 3: Creating patient EMR entries...")
        print("-" * 60)
        emr_count = seed_emrs(db, patient_ids, doctor_ids)
        
        # Summary
        print("=" * 60)
        print("Seeding Complete!")
        print("=" * 60)
        print(f"✓ Created {len(doctor_ids)} doctor accounts")
        print(f"✓ Created {len(patient_ids)} patient accounts")
        print(f"✓ Created {emr_count} EMR entries")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if 'client' in locals():
            client.close()
            print("\n✓ Database connection closed")


if __name__ == "__main__":
    main()

