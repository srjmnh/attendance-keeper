import os
from app import create_app
from werkzeug.security import generate_password_hash

# Create the Flask application instance
app = create_app(os.getenv('FLASK_CONFIG', 'default'))

def create_default_admin():
    """Creates a default admin user if no admin exists"""
    try:
        from app.services.firebase_service import get_user_by_email
        
        # Check if admin exists
        admin = get_user_by_email('admin@example.com')
        
        if not admin:
            default_username = os.getenv('DEFAULT_ADMIN_USERNAME', 'admin')
            default_password = "Admin123!"  # Change this immediately after first login
            password_hash = generate_password_hash(default_password)
            
            admin_data = {
                "email": "admin@example.com",
                "name": "Admin User",
                "password_hash": password_hash,
                "role": "admin"
            }
            
            from app.services.firebase_service import create_user
            create_user(admin_data)
            print(f"Default admin created with username: {default_username}")
            print(f"Password hash: {password_hash}")
        else:
            print("Admin user already exists")
    except Exception as e:
        print(f"Error creating default admin: {str(e)}")

# Initialize services that require app context
with app.app_context():
    # Create default admin if none exists
    create_default_admin()

if __name__ == "__main__":
    # Run the application
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config['DEBUG']) 