import os
from flask import Flask, g
from flask_login import LoginManager
from firebase_admin import credentials, initialize_app, firestore
import base64
import json
from app.services.db_service import DatabaseService
from datetime import timedelta

login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    if not hasattr(g, 'db_service'):
        g.db_service = DatabaseService()
    return g.db_service.get_user_by_id(user_id)

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    DEBUG = False
    TESTING = False
    
    # Firebase configuration
    FIREBASE_CREDENTIALS = os.environ.get('FIREBASE_ADMIN_CREDENTIALS_BASE64')
    
    # AWS configuration
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    
    # Email configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def create_app(config_name=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    app.config.from_object(config[config_name])
    
    # Initialize Firebase Admin SDK
    firebase_creds = os.environ.get('FIREBASE_ADMIN_CREDENTIALS_BASE64')
    if firebase_creds:
        try:
            cred_json = base64.b64decode(firebase_creds).decode('utf-8')
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            firebase_app = initialize_app(cred)
            db = firestore.client()
            app.db = db
        except Exception as e:
            app.logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    with app.app_context():
        from app.routes import auth, main, admin, ai, recognition, attendance, chat
        app.register_blueprint(auth.bp)
        app.register_blueprint(main.bp)
        app.register_blueprint(admin.bp)
        app.register_blueprint(ai.bp)
        app.register_blueprint(recognition.bp)
        app.register_blueprint(attendance.bp)
        app.register_blueprint(chat.bp)
    
    @app.before_request
    def before_request():
        """Set up request context"""
        if not hasattr(g, 'db_service'):
            g.db_service = DatabaseService()
    
    return app 