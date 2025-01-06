import os
import sys
from datetime import datetime

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user import User
from app.services.db_service import DatabaseService

def create_admin():
    """Create a default admin user"""
    # Initialize database service
    db = DatabaseService()
    
    # Check if admin already exists
    admin = db.get_user_by_email('admin@example.com')
    if admin:
        print("Admin user already exists")
        return
    
    # Create admin user
    admin_data = {
        'email': 'admin@example.com',
        'first_name': 'Admin',
        'last_name': 'User',
        'role': 'admin',
        'status': 'active',
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }
    
    admin = User(admin_data)
    admin.set_password('admin123')  # Set default password
    
    # Save to database
    db.create_user(admin)
    print("Admin user created successfully")
    print("Email: admin@example.com")
    print("Password: admin123")

if __name__ == '__main__':
    create_admin() 