from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin):
    """User model for authentication and authorization"""

    def __init__(self, user_data):
        """Initialize user with data from database"""
        self.id = user_data.get('id')
        self.email = user_data.get('email')
        self.first_name = user_data.get('first_name')
        self.last_name = user_data.get('last_name')
        self.role = user_data.get('role', 'student')
        self.class_name = user_data.get('class_name')
        self.division = user_data.get('division')
        self.password_hash = user_data.get('password')
        self.face_id = user_data.get('face_id')

    @property
    def full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}" if self.last_name else self.first_name

    def set_password(self, password):
        """Set user password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if password is correct"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'

    def is_teacher(self):
        """Check if user is teacher"""
        return self.role == 'teacher'

    def is_student(self):
        """Check if user is student"""
        return self.role == 'student'

    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'class_name': self.class_name,
            'division': self.division,
            'password': self.password_hash,
            'face_id': self.face_id
        }

    @staticmethod
    def from_dict(user_dict):
        """Create user object from dictionary"""
        return User(user_dict)

    def update(self, data):
        """Update user attributes"""
        if 'email' in data:
            self.email = data['email']
        if 'first_name' in data:
            self.first_name = data['first_name']
        if 'last_name' in data:
            self.last_name = data['last_name']
        if 'role' in data:
            self.role = data['role']
        if 'class_name' in data:
            self.class_name = data['class_name']
        if 'division' in data:
            self.division = data['division']
        if 'password' in data:
            self.set_password(data['password'])
        if 'face_id' in data:
            self.face_id = data['face_id'] 