import os
from app import create_app
from app.services.db_service import DatabaseService
from werkzeug.security import generate_password_hash

# Create the Flask application instance
app = create_app(os.getenv('FLASK_CONFIG', 'default'))

def create_default_admin():
    """Creates a default admin user if no admin exists"""
    try:
        db = DatabaseService()
        admins = db.get_users_by_role('admin')
        
        if not admins:
            default_username = "admin"
            default_password = "Admin123!"  # Change this immediately after first login
            password_hash = generate_password_hash(default_password)
            
            admin_data = {
                "username": default_username,
                "password_hash": password_hash,
                "role": "admin",
                "classes": []
            }
            
            db.create_user(admin_data)
            print(f"Default admin created with username: {default_username}")
        else:
            print("Admin user already exists")
    except Exception as e:
        print(f"Error creating default admin: {str(e)}")

if __name__ == "__main__":
    # Create default admin if none exists
    with app.app_context():
        create_default_admin()
    
    # Run the application
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config['DEBUG']) 