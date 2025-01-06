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
    print("ERROR: FIREBASE_ADMIN_CREDENTIALS_BASE64 not found in environment", file=sys.stderr)
    raise ValueError("FIREBASE_ADMIN_CREDENTIALS_BASE64 not found in environment.")

print(f"Base64 string length: {len(base64_cred_str)}", file=sys.stderr)
print(f"First 50 chars of base64: {base64_cred_str[:50]}", file=sys.stderr)

try:
    # Try to clean the base64 string
    base64_cred_str = base64_cred_str.strip()
    # Add padding if necessary
    padding = len(base64_cred_str) % 4
    if padding:
        base64_cred_str += '=' * (4 - padding)
    
    decoded_cred_json = base64.b64decode(base64_cred_str)
    print(f"Decoded JSON length: {len(decoded_cred_json)}", file=sys.stderr)
    print(f"First 50 chars of decoded JSON: {decoded_cred_json[:50]}", file=sys.stderr)
    
    # Try to decode as UTF-8 first to see the content
    try:
        json_str = decoded_cred_json.decode('utf-8')
        print(f"Decoded as UTF-8 successfully, first 50 chars: {json_str[:50]}", file=sys.stderr)
    except UnicodeDecodeError as e:
        print(f"Failed to decode as UTF-8: {str(e)}", file=sys.stderr)
    
    cred_dict = json.loads(decoded_cred_json)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
except base64.binascii.Error as e:
    print(f"Base64 decoding error: {str(e)}", file=sys.stderr)
    raise
except json.JSONDecodeError as e:
    print(f"JSON decoding error: {str(e)}", file=sys.stderr)
    raise
except Exception as e:
    print(f"Unexpected error: {str(e)}", file=sys.stderr)
    raise

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