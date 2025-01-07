from flask_login import UserMixin

class User(UserMixin):
    """User model for Flask-Login"""
    
    def __init__(self, id, email, name, role):
        self.id = id
        self.email = email
        self.name = name
        self.role = role
    
    @property
    def is_admin(self):
        """Check if user is an admin"""
        return self.role == 'admin'
    
    @property
    def is_teacher(self):
        """Check if user is a teacher"""
        return self.role == 'teacher'
    
    @property
    def is_student(self):
        """Check if user is a student"""
        return self.role == 'student'
    
    def can_access_subject(self, subject_id):
        """Check if user can access a subject"""
        from app.services.firebase_service import get_user_subjects
        
        try:
            subjects = get_user_subjects(self.id)
            return any(subject.get('id') == subject_id for subject in subjects)
        except Exception:
            return False
    
    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.is_admin
    
    def can_manage_subjects(self):
        """Check if user can manage subjects"""
        return self.is_admin or self.is_teacher
    
    def can_take_attendance(self):
        """Check if user can take attendance"""
        return self.is_admin or self.is_teacher
    
    def can_view_attendance(self, student_id=None):
        """Check if user can view attendance records"""
        if self.is_admin or self.is_teacher:
            return True
        return student_id == self.id
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role
        }
    
    @staticmethod
    def from_dict(data):
        """Create user object from dictionary"""
        return User(
            id=data.get('id'),
            email=data.get('email'),
            name=data.get('name'),
            role=data.get('role')
        ) 