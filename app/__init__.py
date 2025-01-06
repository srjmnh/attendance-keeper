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

# Initialize extensions
login_manager = LoginManager()
cors = CORS()
cache = Cache()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

def initialize_firebase():
    """Initialize Firebase with proper error handling"""
    base64_cred_str = os.environ.get("FIREBASE_ADMIN_CREDENTIALS_BASE64")
    if not base64_cred_str:
        raise ValueError("FIREBASE_ADMIN_CREDENTIALS_BASE64 not found in environment.")
    
    try:
        # Remove any whitespace and newlines
        base64_cred_str = base64_cred_str.strip()
        
        # Add padding if necessary
        padding = len(base64_cred_str) % 4
        if padding:
            base64_cred_str += '=' * (4 - padding)
        
        # Decode base64
        decoded_cred_json = base64.b64decode(base64_cred_str).decode('utf-8')
        
        # Parse JSON
        cred_dict = json.loads(decoded_cred_json)
        
        # Initialize Firebase
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
        return firestore.client()
    except base64.binascii.Error as e:
        raise ValueError(f"Invalid base64 encoding: {str(e)}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format after base64 decode: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error initializing Firebase: {str(e)}")

# Initialize Firebase
db = initialize_firebase()

@login_manager.user_loader
def load_user(user_id):
    from app.models.user import User
    user_data = db.collection('users').document(user_id).get()
    return User.from_dict(user_data.to_dict()) if user_data.exists else None

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