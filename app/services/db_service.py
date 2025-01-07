import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
from flask import current_app
from app.models.user import User
from app.models.subject import Subject
from app.models.attendance import Attendance

class DatabaseService:
    """Service for interacting with Firebase Firestore database"""

    def __init__(self):
        """Initialize Firebase with credentials"""
        try:
            if not firebase_admin._apps:
                cred_base64 = os.environ.get('FIREBASE_CREDENTIALS_BASE64')
                if not cred_base64:
                    raise ValueError("Firebase credentials not found in environment variables")
                
                # Decode base64 credentials
                cred_json = base64.b64decode(cred_base64).decode('utf-8')
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
                
                # Initialize Firebase
                firebase_admin.initialize_app(cred)
            
            self.db = firestore.client()
            self.users_ref = self.db.collection('users')
            self.subjects_ref = self.db.collection('subjects')
            self.attendance_ref = self.db.collection('attendance')
            
        except Exception as e:
            current_app.logger.error(f"Error initializing Firebase: {str(e)}")
            raise

    # User operations
    def create_user(self, user_data):
        """Create a new user"""
        try:
            doc_ref = self.users_ref.document()
            user_data['id'] = doc_ref.id
            doc_ref.set(user_data)
            return User.from_dict(user_data)
        except Exception as e:
            current_app.logger.error(f"Error creating user: {str(e)}")
            raise

    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            doc = self.users_ref.document(user_id).get()
            return User.from_dict(doc.to_dict()) if doc.exists else None
        except Exception as e:
            current_app.logger.error(f"Error getting user {user_id}: {str(e)}")
            return None

    def get_user_by_email(self, email):
        """Get user by email"""
        try:
            query = self.users_ref.where('email', '==', email).limit(1)
            docs = query.stream()
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                return User.from_dict(data)
            return None
        except Exception as e:
            current_app.logger.error(f"Error getting user by email {email}: {str(e)}")
            return None

    def update_user(self, user_id, user_data):
        """Update user data"""
        try:
            self.users_ref.document(user_id).update(user_data)
            return True
        except Exception as e:
            current_app.logger.error(f"Error updating user {user_id}: {str(e)}")
            return False

    def delete_user(self, user_id):
        """Delete user"""
        try:
            self.users_ref.document(user_id).delete()
            return True
        except Exception as e:
            current_app.logger.error(f"Error deleting user {user_id}: {str(e)}")
            return False

    def get_all_users(self):
        """Get all users"""
        try:
            users = []
            docs = self.users_ref.stream()
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                users.append(User.from_dict(data))
            return users
        except Exception as e:
            current_app.logger.error(f"Error getting all users: {str(e)}")
            return []

    def get_all_teachers(self):
        """Get all teachers"""
        try:
            teachers = []
            query = self.users_ref.where('role', '==', 'teacher')
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                teachers.append(User.from_dict(data))
            return teachers
        except Exception as e:
            current_app.logger.error(f"Error getting teachers: {str(e)}")
            return []

    # Subject operations
    def create_subject(self, subject_data):
        """Create a new subject"""
        try:
            doc_ref = self.subjects_ref.document()
            subject_data['id'] = doc_ref.id
            doc_ref.set(subject_data)
            return Subject.from_dict(subject_data)
        except Exception as e:
            current_app.logger.error(f"Error creating subject: {str(e)}")
            raise

    def get_subject_by_id(self, subject_id):
        """Get subject by ID"""
        try:
            doc = self.subjects_ref.document(subject_id).get()
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return Subject.from_dict(data)
            return None
        except Exception as e:
            current_app.logger.error(f"Error getting subject {subject_id}: {str(e)}")
            return None

    def update_subject(self, subject_id, subject_data):
        """Update subject data"""
        try:
            self.subjects_ref.document(subject_id).update(subject_data)
            return True
        except Exception as e:
            current_app.logger.error(f"Error updating subject {subject_id}: {str(e)}")
            return False

    def delete_subject(self, subject_id):
        """Delete subject"""
        try:
            self.subjects_ref.document(subject_id).delete()
            return True
        except Exception as e:
            current_app.logger.error(f"Error deleting subject {subject_id}: {str(e)}")
            return False

    def get_all_subjects(self):
        """Get all subjects"""
        try:
            subjects = []
            docs = self.subjects_ref.stream()
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                subjects.append(Subject.from_dict(data))
            return subjects
        except Exception as e:
            current_app.logger.error(f"Error getting all subjects: {str(e)}")
            return []

    def get_teacher_subjects(self, teacher_id):
        """Get subjects taught by a teacher"""
        try:
            subjects = []
            query = self.subjects_ref.where('teacher_id', '==', teacher_id)
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                subjects.append(Subject.from_dict(data))
            return subjects
        except Exception as e:
            current_app.logger.error(f"Error getting teacher subjects: {str(e)}")
            return []

    def get_student_subjects(self, student_id):
        """Get subjects for a student"""
        try:
            student = self.get_user_by_id(student_id)
            if not student:
                return []
            
            subjects = []
            query = self.subjects_ref.where('class_name', '==', student.class_name)\
                                   .where('division', '==', student.division)
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                subjects.append(Subject.from_dict(data))
            return subjects
        except Exception as e:
            current_app.logger.error(f"Error getting student subjects: {str(e)}")
            return []

    # Attendance operations
    def mark_attendance(self, attendance_data):
        """Mark attendance for a student"""
        try:
            doc_ref = self.attendance_ref.document()
            attendance_data['id'] = doc_ref.id
            attendance_data['date'] = datetime.utcnow().isoformat()
            doc_ref.set(attendance_data)
            return Attendance.from_dict(attendance_data)
        except Exception as e:
            current_app.logger.error(f"Error marking attendance: {str(e)}")
            raise

    def get_attendance_by_id(self, attendance_id):
        """Get attendance record by ID"""
        try:
            doc = self.attendance_ref.document(attendance_id).get()
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return Attendance.from_dict(data)
            return None
        except Exception as e:
            current_app.logger.error(f"Error getting attendance {attendance_id}: {str(e)}")
            return None

    def update_attendance(self, attendance_id, attendance_data):
        """Update attendance record"""
        try:
            self.attendance_ref.document(attendance_id).update(attendance_data)
            return True
        except Exception as e:
            current_app.logger.error(f"Error updating attendance {attendance_id}: {str(e)}")
            return False

    def delete_attendance(self, attendance_id):
        """Delete attendance record"""
        try:
            self.attendance_ref.document(attendance_id).delete()
            return True
        except Exception as e:
            current_app.logger.error(f"Error deleting attendance {attendance_id}: {str(e)}")
            return False

    def get_student_attendance(self, student_id, subject_id=None, start_date=None, end_date=None):
        """Get attendance records for a student"""
        try:
            query = self.attendance_ref.where('student_id', '==', student_id)
            
            if subject_id:
                query = query.where('subject_id', '==', subject_id)
            if start_date:
                query = query.where('date', '>=', start_date.isoformat())
            if end_date:
                query = query.where('date', '<=', end_date.isoformat())
            
            records = []
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                records.append(Attendance.from_dict(data))
            return records
        except Exception as e:
            current_app.logger.error(f"Error getting student attendance: {str(e)}")
            return []

    def get_subject_attendance(self, subject_id, date=None):
        """Get attendance records for a subject"""
        try:
            query = self.attendance_ref.where('subject_id', '==', subject_id)
            if date:
                start = datetime.combine(date, datetime.min.time())
                end = start + timedelta(days=1)
                query = query.where('date', '>=', start.isoformat())\
                           .where('date', '<', end.isoformat())
            
            records = []
            for doc in query.stream():
                data = doc.to_dict()
                data['id'] = doc.id
                records.append(Attendance.from_dict(data))
            return records
        except Exception as e:
            current_app.logger.error(f"Error getting subject attendance: {str(e)}")
            return []

    def get_student_attendance_percentage(self, student_id, subject_id=None):
        """Calculate attendance percentage for a student"""
        try:
            query = self.attendance_ref.where('student_id', '==', student_id)
            if subject_id:
                query = query.where('subject_id', '==', subject_id)
            
            total = 0
            present = 0
            for doc in query.stream():
                total += 1
                if doc.to_dict().get('status') in ['present', 'late']:
                    present += 1
            
            return (present / total * 100) if total > 0 else 0
        except Exception as e:
            current_app.logger.error(f"Error calculating attendance percentage: {str(e)}")
            return 0

    def get_teacher_attendance_stats(self, teacher_id):
        """Get attendance statistics for a teacher's subjects"""
        try:
            stats = {
                'total_students': 0,
                'average_attendance': 0,
                'subject_stats': {}
            }
            
            # Get teacher's subjects
            subjects = self.get_teacher_subjects(teacher_id)
            if not subjects:
                return stats
            
            total_percentage = 0
            total_subjects = len(subjects)
            
            for subject in subjects:
                subject_stats = {
                    'total_classes': 0,
                    'total_students': 0,
                    'average_attendance': 0
                }
                
                # Get attendance records for subject
                records = self.get_subject_attendance(subject.id)
                if records:
                    subject_stats['total_classes'] = len(set(r.date.date() for r in records))
                    subject_stats['total_students'] = len(set(r.student_id for r in records))
                    present_count = len([r for r in records if r.status in ['present', 'late']])
                    subject_stats['average_attendance'] = (present_count / len(records) * 100) if records else 0
                    
                stats['subject_stats'][subject.id] = subject_stats
                total_percentage += subject_stats['average_attendance']
                stats['total_students'] += subject_stats['total_students']
            
            stats['average_attendance'] = total_percentage / total_subjects if total_subjects > 0 else 0
            return stats
        except Exception as e:
            current_app.logger.error(f"Error getting teacher attendance stats: {str(e)}")
            return None

    def get_system_attendance_stats(self):
        """Get system-wide attendance statistics"""
        try:
            stats = {
                'total_students': 0,
                'total_subjects': 0,
                'average_attendance': 0,
                'class_stats': {}
            }
            
            # Get total counts
            students = self.users_ref.where('role', '==', 'student').stream()
            stats['total_students'] = len(list(students))
            
            subjects = self.subjects_ref.stream()
            stats['total_subjects'] = len(list(subjects))
            
            # Calculate overall attendance
            total_records = 0
            present_records = 0
            
            for doc in self.attendance_ref.stream():
                total_records += 1
                if doc.to_dict().get('status') in ['present', 'late']:
                    present_records += 1
            
            stats['average_attendance'] = (present_records / total_records * 100) if total_records > 0 else 0
            return stats
        except Exception as e:
            current_app.logger.error(f"Error getting system attendance stats: {str(e)}")
            return None 