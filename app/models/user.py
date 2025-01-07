from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data.get('id')
        self.email = user_data.get('email')
        self.password = user_data.get('password')
        self.first_name = user_data.get('first_name')
        self.last_name = user_data.get('last_name')
        self.role = user_data.get('role')
        self.status = user_data.get('status', 'active')
        self.class_name = user_data.get('class_name')
        self.division = user_data.get('division')
        self.face_id = user_data.get('face_id')
        self.created_at = user_data.get('created_at')
        self.updated_at = user_data.get('updated_at')

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def is_active(self):
        return self.status == 'active'

    def is_admin(self):
        return self.role == 'admin'

    def is_teacher(self):
        return self.role == 'teacher'

    def is_student(self):
        return self.role == 'student'

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'password': self.password,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'status': self.status,
            'class_name': self.class_name,
            'division': self.division,
            'face_id': self.face_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @staticmethod
    def from_dict(user_dict):
        return User(user_dict) 