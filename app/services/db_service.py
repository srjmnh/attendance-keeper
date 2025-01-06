import logging
from datetime import datetime
from typing import Dict, List, Optional, Union
from flask import current_app

import firebase_admin
from firebase_admin import credentials, firestore

from .firebase_service import get_firebase_credentials

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        """Initialize Firebase connection"""
        self.initialized = False
        try:
            if not firebase_admin._apps:
                # Initialize Firebase with credentials from environment
                cred = credentials.Certificate(get_firebase_credentials())
                firebase_admin.initialize_app(cred, {
                    'databaseURL': current_app.config.get('FIREBASE_DATABASE_URL', 'https://facial-f5096.firebaseio.com')
                })
            
            self.db = firestore.client()
            self._initialize_collections()
            self.initialized = True
            logger.info("Firebase initialized successfully!")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise

    def _check_initialized(self):
        """Check if service is initialized"""
        if not self.initialized:
            raise RuntimeError("Database service not properly initialized")

    def _initialize_collections(self) -> None:
        """Initialize database collections if they don't exist"""
        collections = ['users', 'attendance', 'subjects']
        for collection in collections:
            if not self.db.collection(collection).get():
                logger.info(f"Initializing collection: {collection}")

    # User Management Methods
    def create_user(self, username: str, password: str, role: str, classes: List[str] = None) -> str:
        """Create a new user"""
        self._check_initialized()
        try:
            # Check if username exists
            existing = self.db.collection('users').where('username', '==', username).get()
            if any(existing):
                raise ValueError("Username already exists")

            # Create user document
            user_data = {
                'username': username,
                'password': password,
                'role': role,
                'classes': classes or [],
                'created_at': datetime.utcnow().isoformat()
            }
            
            doc_ref = self.db.collection('users').document()
            doc_ref.set(user_data)
            return doc_ref.id
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise

    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        self._check_initialized()
        try:
            doc = self.db.collection('users').document(user_id).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            raise

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        try:
            users = self.db.collection('users').where('username', '==', username).get()
            for user in users:
                return {'id': user.id, **user.to_dict()}
            return None
        except Exception as e:
            logger.error(f"Error getting user by username: {str(e)}")
            raise

    # Subject Management Methods
    def create_subject(self, name: str, code: str = None) -> str:
        """Create a new subject"""
        try:
            # Generate code if not provided
            if not code:
                code = ''.join(word[0].upper() for word in name.split()[:3])
                code = code.ljust(3, 'X')[:3]

            # Check if code exists
            existing = self.db.collection('subjects').where('code', '==', code).get()
            if any(existing):
                raise ValueError(f"Subject code '{code}' already exists")

            subject_data = {
                'name': name,
                'code': code,
                'created_at': datetime.utcnow().isoformat()
            }
            
            doc_ref = self.db.collection('subjects').document()
            doc_ref.set(subject_data)
            return doc_ref.id
            
        except Exception as e:
            logger.error(f"Error creating subject: {str(e)}")
            raise

    def get_subjects(self, teacher_classes: List[str] = None) -> List[Dict]:
        """Get all subjects"""
        try:
            query = self.db.collection('subjects')
            if teacher_classes:
                query = query.where('code', 'in', teacher_classes)
            
            subjects = []
            for doc in query.get():
                subjects.append({'id': doc.id, **doc.to_dict()})
            return subjects
            
        except Exception as e:
            logger.error(f"Error getting subjects: {str(e)}")
            raise

    # Attendance Management Methods
    def log_attendance(self, attendance_data: Dict) -> str:
        """Log attendance record"""
        try:
            # Validate required fields
            required = ['student_id', 'name', 'subject_id', 'subject_name']
            if not all(key in attendance_data for key in required):
                raise ValueError("Missing required attendance data fields")

            # Add timestamp and status
            attendance_data.update({
                'timestamp': attendance_data.get('timestamp', datetime.utcnow().isoformat()),
                'status': attendance_data.get('status', 'PRESENT')
            })
            
            doc_ref = self.db.collection('attendance').document()
            doc_ref.set(attendance_data)
            return doc_ref.id
            
        except Exception as e:
            logger.error(f"Error logging attendance: {str(e)}")
            raise

    def get_attendance(self, 
                      student_id: str = None,
                      subject_id: str = None,
                      start_date: str = None,
                      end_date: str = None,
                      teacher_classes: List[str] = None) -> List[Dict]:
        """Get attendance records"""
        try:
            query = self.db.collection('attendance')
            
            # Apply filters
            if student_id:
                query = query.where('student_id', '==', student_id)
            if subject_id:
                query = query.where('subject_id', '==', subject_id)
            if teacher_classes:
                query = query.where('subject_id', 'in', teacher_classes)
            if start_date:
                query = query.where('timestamp', '>=', start_date)
            if end_date:
                query = query.where('timestamp', '<=', end_date)
            
            records = []
            for doc in query.get():
                records.append({'id': doc.id, **doc.to_dict()})
            return records
            
        except Exception as e:
            logger.error(f"Error getting attendance records: {str(e)}")
            raise

    def update_attendance(self, record_id: str, updates: Dict) -> bool:
        """Update attendance record"""
        try:
            doc_ref = self.db.collection('attendance').document(record_id)
            if not doc_ref.get().exists:
                raise ValueError("Attendance record not found")
                
            doc_ref.update(updates)
            return True
            
        except Exception as e:
            logger.error(f"Error updating attendance: {str(e)}")
            raise

    def delete_attendance(self, record_id: str) -> bool:
        """Delete attendance record"""
        try:
            doc_ref = self.db.collection('attendance').document(record_id)
            if not doc_ref.get().exists:
                raise ValueError("Attendance record not found")
                
            doc_ref.delete()
            return True
            
        except Exception as e:
            logger.error(f"Error deleting attendance: {str(e)}")
            raise