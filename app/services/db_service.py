import logging
from datetime import datetime
from typing import Dict, List, Optional
from flask import current_app

import firebase_admin
from firebase_admin import credentials, firestore

from .firebase_service import get_firebase_credentials

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        """Initialize Firebase connection"""
        self.initialized = False
        self.db = None
        
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(get_firebase_credentials())
                firebase_admin.initialize_app(cred)
            
            self.db = firestore.client()
            self.initialized = True
            logger.info("Firebase initialized successfully!")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            pass

    def record_attendance(self, student_id: str, subject_code: str) -> bool:
        """Record attendance for a student"""
        if not self.db:
            logger.error("Database not initialized")
            return False
            
        try:
            # Create attendance record
            attendance_data = {
                'student_id': student_id,
                'subject_code': subject_code,
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'PRESENT'
            }
            
            # Add to attendance collection
            self.db.collection('attendance').add(attendance_data)
            logger.info(f"Recorded attendance for student {student_id} in {subject_code}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording attendance: {str(e)}")
            return False

    def get_student_info(self, student_id: str) -> Optional[Dict]:
        """Get student information"""
        if not self.db:
            return None
            
        try:
            doc = self.db.collection('students').document(student_id).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"Error getting student info: {str(e)}")
            return None

    def register_student(self, student_id: str, name: str, face_id: str) -> bool:
        """Register a new student"""
        if not self.db:
            return False
            
        try:
            student_data = {
                'name': name,
                'face_id': face_id,
                'registered_at': datetime.utcnow().isoformat()
            }
            
            self.db.collection('students').document(student_id).set(student_data)
            logger.info(f"Registered student {name} with ID {student_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering student: {str(e)}")
            return False

    def get_subject_info(self, subject_code: str) -> Optional[Dict]:
        """Get subject information"""
        if not self.db:
            return None
            
        try:
            doc = self.db.collection('subjects').document(subject_code).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"Error getting subject info: {str(e)}")
            return None