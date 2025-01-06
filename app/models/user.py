from datetime import datetime
from typing import Optional, List, Dict, Any
from flask_login import UserMixin
from sqlalchemy.ext.hybrid import hybrid_property
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from app import db
from app.constants import UserRole, UserStatus
from app.utils import get_gravatar_url

class User(UserMixin, db.Model):
    """User model for storing user account information"""
    __tablename__ = 'users'
    
    # Basic fields
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    _password = db.Column('password', db.String(128), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=UserRole.STUDENT.value)
    status = db.Column(db.String(20), nullable=False, default=UserStatus.PENDING.value)
    
    # Additional fields
    phone = db.Column(db.String(20))
    profile_photo = db.Column(db.String(255))
    bio = db.Column(db.Text)
    department = db.Column(db.String(100))
    student_id = db.Column(db.String(50), unique=True)
    
    # Authentication fields
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100))
    password_reset_token = db.Column(db.String(100))
    password_reset_expires = db.Column(db.DateTime)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    subjects = db.relationship('Subject', backref='teacher', lazy='dynamic',
                             foreign_keys='Subject.teacher_id')
    attendances = db.relationship('Attendance', backref='student', lazy='dynamic',
                                foreign_keys='Attendance.student_id')
    notifications = db.relationship('Notification', backref='recipient', lazy='dynamic',
                                  foreign_keys='Notification.recipient_id')
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.profile_photo is None:
            self.profile_photo = get_gravatar_url(self.email)
    
    @hybrid_property
    def password(self) -> str:
        """Get password hash"""
        return self._password
    
    @password.setter
    def password(self, password: str) -> None:
        """Set password hash"""
        self._password = generate_password_hash(password)
    
    @hybrid_property
    def full_name(self) -> str:
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def check_password(self, password: str) -> bool:
        """Check if password matches"""
        return check_password_hash(self._password, password)
    
    def generate_auth_token(self, expires_in: int = 3600) -> str:
        """Generate authentication token"""
        return jwt.encode(
            {
                'id': self.id,
                'email': self.email,
                'role': self.role,
                'exp': datetime.utcnow() + datetime.timedelta(seconds=expires_in)
            },
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
    
    @staticmethod
    def verify_auth_token(token: str) -> Optional['User']:
        """Verify authentication token"""
        try:
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            return User.query.get(data['id'])
        except:
            return None
    
    def generate_email_verification_token(self) -> str:
        """Generate email verification token"""
        self.email_verification_token = jwt.encode(
            {
                'email': self.email,
                'exp': datetime.utcnow() + datetime.timedelta(days=7)
            },
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        return self.email_verification_token
    
    def verify_email(self, token: str) -> bool:
        """Verify email with token"""
        try:
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            if data['email'] == self.email:
                self.email_verified = True
                self.email_verification_token = None
                db.session.commit()
                return True
            return False
        except:
            return False
    
    def generate_password_reset_token(self) -> str:
        """Generate password reset token"""
        self.password_reset_token = jwt.encode(
            {
                'id': self.id,
                'exp': datetime.utcnow() + datetime.timedelta(hours=24)
            },
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        self.password_reset_expires = datetime.utcnow() + datetime.timedelta(hours=24)
        db.session.commit()
        return self.password_reset_token
    
    def verify_password_reset_token(self, token: str) -> bool:
        """Verify password reset token"""
        if (not self.password_reset_token or
            not self.password_reset_expires or
            datetime.utcnow() > self.password_reset_expires):
            return False
        try:
            data = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            return data['id'] == self.id
        except:
            return False
    
    def record_login(self, success: bool = True) -> None:
        """Record login attempt"""
        if success:
            self.failed_login_attempts = 0
            self.locked_until = None
            self.last_login = datetime.utcnow()
        else:
            self.failed_login_attempts += 1
            if self.failed_login_attempts >= 5:
                self.locked_until = datetime.utcnow() + datetime.timedelta(minutes=30)
        db.session.commit()
    
    def is_locked(self) -> bool:
        """Check if account is locked"""
        if self.locked_until and datetime.utcnow() < self.locked_until:
            return True
        if self.locked_until:
            self.locked_until = None
            self.failed_login_attempts = 0
            db.session.commit()
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'role': self.role,
            'status': self.status,
            'phone': self.phone,
            'profile_photo': self.profile_photo,
            'bio': self.bio,
            'department': self.department,
            'student_id': self.student_id,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def __repr__(self) -> str:
        """String representation of user"""
        return f'<User {self.email}>' 