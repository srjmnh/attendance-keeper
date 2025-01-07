from flask import Flask
from flask_login import LoginManager
from app.config import config
from app.models.user import User
from app.services.firebase_service import initialize_firebase

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    from app.services.db_service import DatabaseService
    db = DatabaseService()
    return db.get_user_by_id(user_id)

def create_app(config_name='default'):
    """Application factory function"""
    app = Flask(__name__)
    
    # Load config
    app.config.from_object(config[config_name])
    
    # Initialize Firebase with credentials from environment
    credentials_base64 = app.config['FIREBASE_ADMIN_CREDENTIALS_BASE64']
    if not credentials_base64:
        raise ValueError("FIREBASE_ADMIN_CREDENTIALS_BASE64 not found in environment variables")
    initialize_firebase(credentials_base64)
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    
    # Register blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.teacher import teacher_bp
    from app.blueprints.student import student_bp
    from app.blueprints.main import main_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(main_bp)
    
    return app 