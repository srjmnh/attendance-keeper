import firebase_admin
from firebase_admin import firestore
from datetime import datetime
import logging
from ..models.user import User
from ..models.subject import Subject
from ..models.attendance import Attendance

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.db = firestore.client()
        self._setup_collections()

    def _setup_collections(self):
        """Setup collection references"""
        self.users_ref = self.db.collection('users')
        self.subjects_ref = self.db.collection('subjects')
        self.attendance_ref = self.db.collection('attendance')

    # User operations
    def create_user(self, user):
        """Create a new user"""
        try:
            doc_ref = self.users_ref.document()
            user.id = doc_ref.id
            user_dict = user.to_dict()
            doc_ref.set(user_dict)
            logger.info(f"Created user with ID: {user.id}")
            return user_dict
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise

    def get_user(self, user_id):
        """Get user by ID"""
        try:
            doc = self.users_ref.document(user_id).get()
            if doc.exists:
                user_dict = doc.to_dict()
                user_dict['id'] = doc.id
                logger.info(f"Retrieved user with ID: {user_id}")
                return user_dict
            logger.warning(f"No user found with ID: {user_id}")
            return None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            raise

    def get_user_by_email(self, email):
        """Get user by email"""
        try:
            users = self.users_ref.where('email', '==', email).limit(1).stream()
            for doc in users:
                user_dict = doc.to_dict()
                user_dict['id'] = doc.id
                logger.info(f"Retrieved user with email: {email}")
                return user_dict
            logger.warning(f"No user found with email: {email}")
            return None
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            raise

    def update_user(self, user_id, update_data):
        """Update user"""
        try:
            self.users_ref.document(user_id).update(update_data)
            logger.info(f"Updated user with ID: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            raise

    def delete_user(self, user_id):
        """Delete user"""
        self.users_ref.document(user_id).delete()

    def list_users(self, role=None):
        """List all users, optionally filtered by role"""
        query = self.users_ref
        if role:
            query = query.where('role', '==', role)
        users = []
        for doc in query.stream():
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            users.append(User.from_dict(user_data))
        return users

    # Subject operations
    def create_subject(self, subject):
        """Create a new subject"""
        doc_ref = self.subjects_ref.document()
        subject.id = doc_ref.id
        doc_ref.set(subject.to_dict())
        return subject

    def get_subject(self, subject_id):
        """Get subject by ID"""
        doc = self.subjects_ref.document(subject_id).get()
        if doc.exists:
            return Subject.from_dict(doc.to_dict())
        return None

    def update_subject(self, subject):
        """Update subject"""
        self.subjects_ref.document(subject.id).update(subject.to_dict())
        return subject

    def delete_subject(self, subject_id):
        """Delete subject"""
        self.subjects_ref.document(subject_id).delete()

    def list_subjects(self, teacher_id=None, class_name=None, division=None):
        """List subjects with optional filters"""
        query = self.subjects_ref
        if teacher_id:
            query = query.where('teacher_id', '==', teacher_id)
        if class_name:
            query = query.where('class_name', '==', class_name)
        if division:
            query = query.where('division', '==', division)
        
        subjects = []
        for doc in query.stream():
            subject_data = doc.to_dict()
            subject_data['id'] = doc.id
            subjects.append(Subject.from_dict(subject_data))
        return subjects

    # Attendance operations
    def create_attendance(self, attendance):
        """Create a new attendance record"""
        doc_ref = self.attendance_ref.document()
        attendance.id = doc_ref.id
        doc_ref.set(attendance.to_dict())
        return attendance

    def get_attendance(self, attendance_id):
        """Get attendance by ID"""
        doc = self.attendance_ref.document(attendance_id).get()
        if doc.exists:
            return Attendance.from_dict(doc.to_dict())
        return None

    def update_attendance(self, attendance):
        """Update attendance"""
        self.attendance_ref.document(attendance.id).update(attendance.to_dict())
        return attendance

    def delete_attendance(self, attendance_id):
        """Delete attendance"""
        self.attendance_ref.document(attendance_id).delete()

    def list_attendance(self, student_id=None, subject_id=None, start_date=None, end_date=None):
        """List attendance records with optional filters"""
        query = self.attendance_ref
        if student_id:
            query = query.where('student_id', '==', student_id)
        if subject_id:
            query = query.where('subject_id', '==', subject_id)
        if start_date:
            query = query.where('date', '>=', start_date.isoformat())
        if end_date:
            query = query.where('date', '<=', end_date.isoformat())
        
        attendance_records = []
        for doc in query.stream():
            attendance_data = doc.to_dict()
            attendance_data['id'] = doc.id
            attendance_records.append(Attendance.from_dict(attendance_data))
        return attendance_records

    def get_attendance_stats(self, student_id, subject_id=None, start_date=None, end_date=None):
        """Get attendance statistics for a student"""
        query = self.attendance_ref.where('student_id', '==', student_id)
        if subject_id:
            query = query.where('subject_id', '==', subject_id)
        if start_date:
            query = query.where('date', '>=', start_date.isoformat())
        if end_date:
            query = query.where('date', '<=', end_date.isoformat())

        total = 0
        present = 0
        for doc in query.stream():
            total += 1
            if doc.to_dict()['status'] == 'present':
                present += 1

        return {
            'total': total,
            'present': present,
            'absent': total - present,
            'percentage': (present / total * 100) if total > 0 else 0
        } 