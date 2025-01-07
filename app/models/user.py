from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class User(UserMixin):
    """User model for authentication and authorization"""

    def __init__(self, user_data):
        """Initialize user with data from database"""
        try:
            if not isinstance(user_data, dict):
                raise ValueError("user_data must be a dictionary")
            
            self.id = user_data.get('id')
            self.email = user_data.get('email')
            self.first_name = user_data.get('first_name', '')
            self.last_name = user_data.get('last_name', '')
            self.role = user_data.get('role', 'student')
            self.class_name = user_data.get('class_name')
            self.division = user_data.get('division')
            self.password_hash = user_data.get('password')
            self.status = user_data.get('status', 'active')
            
            # Validate required fields
            if not self.email:
                raise ValueError("Email is required")
            if not self.role:
                raise ValueError("Role is required")
                
            logger.info(f"User object created for {self.email} with role {self.role}")
        except Exception as e:
            logger.error(f"Error creating user object: {str(e)}")
            raise

    @property
    def full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}" if self.last_name else self.first_name

    def set_password(self, password):
        """Set user password - this will hash the password"""
        try:
            if not password:
                logger.error("Attempted to set empty password")
                raise ValueError("Password cannot be empty")
            self.password_hash = generate_password_hash(password)
            logger.info(f"Password set for user {self.email}")
        except Exception as e:
            logger.error(f"Error setting password for {self.email}: {str(e)}")
            raise

    def check_password(self, password):
        """Check if password is correct"""
        try:
            if not self.password_hash:
                logger.warning(f"No password hash found for user {self.email}")
                return False
            if not password:
                logger.warning(f"Empty password provided for user {self.email}")
                return False
            
            result = check_password_hash(self.password_hash, password)
            logger.info(f"Password check for {self.email}: {'success' if result else 'failed'}")
            return result
        except Exception as e:
            logger.error(f"Error checking password for {self.email}: {str(e)}")
            return False

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
        try:
            data = {
                'id': self.id,
                'email': self.email,
                'first_name': self.first_name,
                'last_name': self.last_name,
                'role': self.role,
                'class_name': self.class_name,
                'division': self.division,
                'password': self.password_hash,
                'status': self.status,
                'updated_at': datetime.utcnow().isoformat()
            }
            logger.info(f"Converting user {self.email} to dictionary")
            return data
        except Exception as e:
            logger.error(f"Error converting user {self.email} to dictionary: {str(e)}")
            raise

    @staticmethod
    def from_dict(user_dict):
        """Create user object from dictionary"""
        try:
            if not user_dict:
                raise ValueError("user_dict cannot be None")
            logger.info(f"Creating user object from dictionary with email: {user_dict.get('email')}")
            return User(user_dict)
        except Exception as e:
            logger.error(f"Error creating user from dictionary: {str(e)}")
            raise 