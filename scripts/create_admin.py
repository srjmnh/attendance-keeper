import os
import sys
from datetime import datetime
import logging

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user import User
from app.services.db_service import DatabaseService

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin():
    """Create a default admin user"""
    try:
        # Initialize database service
        db = DatabaseService()
        
        # Admin credentials
        email = "admin@attendance.com"
        password = "Admin@123"  # More secure password
        
        # Check if admin already exists
        existing_admin = db.get_user_by_email(email)
        if existing_admin:
            logger.info("Admin user already exists")
            return
        
        # Create admin user data
        admin_data = {
            'email': email,
            'first_name': 'System',
            'last_name': 'Admin',
            'role': 'admin',
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Create User object and set password
        admin = User(admin_data)
        admin.set_password(password)
        
        # Convert to dictionary for database storage
        admin_dict = admin.to_dict()
        
        # Save to database
        db.create_user(admin_dict)
        
        logger.info("Admin user created successfully")
        logger.info(f"Email: {email}")
        logger.info(f"Password: {password}")
        
        print("\nAdmin Account Created:")
        print(f"Email: {email}")
        print(f"Password: {password}")
        print("\nPlease save these credentials!")
        
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    create_admin() 