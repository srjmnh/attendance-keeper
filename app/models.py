from flask_login import UserMixin
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class User(UserMixin):
    id: str
    email: str
    password: str
    role: str
    student_id: Optional[str] = None
    classes: List[str] = field(default_factory=list)
    created_at: Optional[str] = None

    def is_admin(self):
        return self.role == 'admin'

    def is_teacher(self):
        return self.role == 'teacher'

    def is_student(self):
        return self.role == 'student'

    @staticmethod
    def from_dict(data, id):
        """Create a User object from a dictionary."""
        return User(
            id=id,
            email=data.get('email'),
            password=data.get('password'),
            role=data.get('role'),
            student_id=data.get('student_id'),
            classes=data.get('classes', []),
            created_at=data.get('created_at')
        )

    def to_dict(self):
        """Convert the User object to a dictionary."""
        return {
            'email': self.email,
            'password': self.password,
            'role': self.role,
            'student_id': self.student_id,
            'classes': self.classes,
            'created_at': self.created_at
        } 