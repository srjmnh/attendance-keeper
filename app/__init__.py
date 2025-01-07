from flask import Flask, render_template
from flask_login import LoginManager
from flask_cors import CORS
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import os
import sys
import logging
import urllib.parse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize extensions
login_manager = LoginManager()
cors = CORS()
cache = Cache()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Initialize Firebase
base64_cred_str = os.environ.get("FIREBASE_ADMIN_CREDENTIALS_BASE64")
if not base64_cred_str:
    logger.error("FIREBASE_ADMIN_CREDENTIALS_BASE64 not found in environment")
    raise ValueError("FIREBASE_ADMIN_CREDENTIALS_BASE64 not found in environment.")

try:
    logger.info(f"Base64 string length: {len(base64_cred_str)}")
    logger.info(f"First 50 chars of base64: {base64_cred_str[:50]}")
    
    # Decode base64 credentials
    cred_json = base64.b64decode(base64_cred_str)
    logger.info(f"Decoded JSON length: {len(cred_json)}")
    
    # Parse JSON
    cred_dict = json.loads(cred_json)
    logger.info(f"Project ID: {cred_dict.get('project_id')}")
    
    # Initialize Firebase Admin
    if not firebase_admin._apps:
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase initialized successfully")
    else:
        logger.info("Firebase already initialized")
    
    # Test Firestore connection
    db = firestore.client()
    logger.info("Firestore client created successfully")
    
except Exception as e:
    logger.error(f"Firebase initialization error: {str(e)}")
    raise

@login_manager.user_loader
def load_user(user_id):
    from app.services.db_service import DatabaseService
    from app.models.user import User
    try:
        db = DatabaseService()
        user_dict = db.get_user_by_id(user_id)
        if user_dict:
            return User(user_dict)
        return None
    except Exception as e:
        logger.error(f"Error loading user {user_id}: {str(e)}")
        return None

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('app.config.Config')
    
    # Initialize extensions
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    cors.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)
    
    # Register blueprints
    from app.routes.main import main
    from app.routes.auth import auth
    from app.routes.attendance import attendance
    from app.routes.recognition import recognition
    from app.routes.subject import subject
    from app.routes.admin import admin
    from app.routes.chat import chat
    
    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(attendance, url_prefix='/attendance')
    app.register_blueprint(recognition, url_prefix='/recognition')
    app.register_blueprint(subject, url_prefix='/subject')
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(chat, url_prefix='/chat')
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
    
    # Create upload directories
    with app.app_context():
        import os
        upload_dirs = ['uploads', 'v1face_temp']
        for directory in upload_dirs:
            os.makedirs(os.path.join(app.root_path, directory), exist_ok=True)
    
    return app 