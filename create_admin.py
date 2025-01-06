from app import create_app, db
from app.models.user import User
from app.constants import UserRole, UserStatus

def create_default_admin():
    """Create default admin user if it doesn't exist"""
    app = create_app()
    
    with app.app_context():
        # Check if admin exists
        admin = User.query.filter_by(email='admin@example.com').first()
        if admin:
            print("Admin user already exists!")
            return
        
        # Create admin user
        admin = User(
            email='admin@example.com',
            password='admin123!@#',  # This will be hashed automatically
            first_name='Admin',
            last_name='User',
            role=UserRole.ADMIN.value,
            status=UserStatus.ACTIVE.value,
            email_verified=True
        )
        
        # Add to database
        db.session.add(admin)
        db.session.commit()
        
        print("Default admin user created successfully!")
        print("Email: admin@example.com")
        print("Password: admin123!@#")

if __name__ == '__main__':
    create_default_admin() 