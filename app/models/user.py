from firebase_admin import firestore
from flask_login import UserMixin
import logging

logger = logging.getLogger(__name__)
db = firestore.client()

class User(UserMixin):
    """User model for Firebase integration"""
    
    def __init__(self, user_id, data):
        self.id = user_id
        self.username = data.get('username')
        self.password_hash = data.get('password_hash')
        self.email = data.get('email')
        self.role = data.get('role', 'student')
        self.name = data.get('name')
        self.is_active = data.get('is_active', True)

    @property
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'

    @property
    def is_teacher(self):
        """Check if user is teacher"""
        return self.role == 'teacher'

    @property
    def is_student(self):
        """Check if user is student"""
        return self.role == 'student'

    @classmethod
    def get_by_id(cls, user_id):
        """Get user by ID"""
        try:
            doc = db.collection('users').document(user_id).get()
            if doc.exists:
                return cls(doc.id, doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            return None

    @classmethod
    def get_by_username(cls, username):
        """Get user by username"""
        try:
            query = db.collection('users').where('username', '==', username).limit(1).get()
            for doc in query:
                return cls(doc.id, doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"Error getting user by username: {str(e)}")
            return None

    @classmethod
    def get_all(cls):
        """Get all users"""
        try:
            users = []
            for doc in db.collection('users').stream():
                users.append(cls(doc.id, doc.to_dict()))
            return users
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}")
            return []

    @classmethod
    def create(cls, username, password_hash, email, role, name):
        """Create a new user"""
        try:
            user_data = {
                'username': username,
                'password_hash': password_hash,
                'email': email,
                'role': role,
                'name': name,
                'is_active': True
            }
            doc_ref = db.collection('users').document()
            doc_ref.set(user_data)
            return cls(doc_ref.id, user_data)
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise

    def update(self, data):
        """Update user data"""
        try:
            db.collection('users').document(self.id).update(data)
            for key, value in data.items():
                setattr(self, key, value)
            return True
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            return False

    def delete(self):
        """Delete user"""
        try:
            db.collection('users').document(self.id).delete()
            return True
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            return False

    def update_password(self, new_password_hash):
        """Update user password"""
        return self.update({'password_hash': new_password_hash})

    def update_email(self, new_email):
        """Update user email"""
        return self.update({'email': new_email})

    def update_role(self, new_role):
        """Update user role"""
        if new_role not in ['admin', 'teacher', 'student']:
            raise ValueError('Invalid role')
        return self.update({'role': new_role})

    def deactivate(self):
        """Deactivate user"""
        return self.update({'is_active': False})

    def activate(self):
        """Activate user"""
        return self.update({'is_active': True})

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'name': self.name,
            'is_active': self.is_active
        } 