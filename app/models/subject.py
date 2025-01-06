from firebase_admin import firestore
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
db = firestore.client()

class Subject:
    """Subject model for Firebase integration"""
    
    def __init__(self, subject_id, data):
        self.id = subject_id
        self.name = data.get('name')
        self.code = data.get('code')
        self.description = data.get('description')
        self.teacher_id = data.get('teacher_id')
        self.created_at = data.get('created_at', datetime.utcnow())
        self.updated_at = data.get('updated_at', datetime.utcnow())
        self.is_active = data.get('is_active', True)

    @classmethod
    def get_by_id(cls, subject_id):
        """Get subject by ID"""
        try:
            doc = db.collection('subjects').document(subject_id).get()
            if doc.exists:
                return cls(doc.id, doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"Error getting subject by ID: {str(e)}")
            return None

    @classmethod
    def get_by_code(cls, code):
        """Get subject by code"""
        try:
            query = db.collection('subjects').where('code', '==', code).limit(1).get()
            for doc in query:
                return cls(doc.id, doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"Error getting subject by code: {str(e)}")
            return None

    @classmethod
    def get_all(cls):
        """Get all subjects"""
        try:
            subjects = []
            for doc in db.collection('subjects').stream():
                subjects.append(cls(doc.id, doc.to_dict()))
            return subjects
        except Exception as e:
            logger.error(f"Error getting all subjects: {str(e)}")
            return []

    @classmethod
    def get_by_teacher(cls, teacher_id):
        """Get subjects by teacher ID"""
        try:
            subjects = []
            query = db.collection('subjects').where('teacher_id', '==', teacher_id).stream()
            for doc in query:
                subjects.append(cls(doc.id, doc.to_dict()))
            return subjects
        except Exception as e:
            logger.error(f"Error getting subjects by teacher: {str(e)}")
            return []

    @classmethod
    def create(cls, name, code, description=None, teacher_id=None):
        """Create a new subject"""
        try:
            subject_data = {
                'name': name,
                'code': code,
                'description': description,
                'teacher_id': teacher_id,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'is_active': True
            }
            doc_ref = db.collection('subjects').document()
            doc_ref.set(subject_data)
            return cls(doc_ref.id, subject_data)
        except Exception as e:
            logger.error(f"Error creating subject: {str(e)}")
            raise

    def update(self, data):
        """Update subject data"""
        try:
            data['updated_at'] = datetime.utcnow()
            db.collection('subjects').document(self.id).update(data)
            for key, value in data.items():
                setattr(self, key, value)
            return True
        except Exception as e:
            logger.error(f"Error updating subject: {str(e)}")
            return False

    def delete(self):
        """Delete subject"""
        try:
            db.collection('subjects').document(self.id).delete()
            return True
        except Exception as e:
            logger.error(f"Error deleting subject: {str(e)}")
            return False

    def deactivate(self):
        """Deactivate subject"""
        return self.update({'is_active': False})

    def activate(self):
        """Activate subject"""
        return self.update({'is_active': True})

    def assign_teacher(self, teacher_id):
        """Assign teacher to subject"""
        return self.update({'teacher_id': teacher_id})

    def get_attendance_stats(self, start_date=None, end_date=None):
        """Get attendance statistics for the subject"""
        try:
            query = db.collection('attendance').where('subject_id', '==', self.id)
            
            if start_date:
                query = query.where('timestamp', '>=', start_date)
            if end_date:
                query = query.where('timestamp', '<=', end_date)

            records = list(query.stream())
            total_records = len(records)
            present_count = len([r for r in records if r.get('status', '').upper() == 'PRESENT'])
            
            return {
                'total_records': total_records,
                'present_count': present_count,
                'absent_count': total_records - present_count,
                'attendance_rate': (present_count / total_records * 100) if total_records > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting attendance stats: {str(e)}")
            return {
                'total_records': 0,
                'present_count': 0,
                'absent_count': 0,
                'attendance_rate': 0
            }

    def to_dict(self):
        """Convert subject to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'teacher_id': self.teacher_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'is_active': self.is_active
        } 