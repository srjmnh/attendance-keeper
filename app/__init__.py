import os
from flask import Flask, g
from flask_login import LoginManager
from firebase_admin import credentials, initialize_app, firestore
import base64
import json
from app.services.db_service import DatabaseService
from datetime import timedelta
import logging
from logging.handlers import RotatingFileHandler
from app.utils.errors import register_error_handlers
from app.services.cache_service import init_cache
from app.utils.rate_limit import init_limiter
from app.utils.monitoring import monitoring_bp
from flask_wtf.csrf import CSRFProtect
from app.utils.filters import init_filters

login_manager = LoginManager()
csrf = CSRFProtect()

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    if not hasattr(g, 'db_service'):
        g.db_service = DatabaseService()
    return g.db_service.get_user_by_id(user_id)

def create_app(config_name=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    if config_name == 'production':
        from app.config.production import ProductionConfig
        app.config.from_object(ProductionConfig)
    else:
        from app.config.development import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)
    
    # Set secret key for CSRF
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-development-only')
    app.config['WTF_CSRF_SECRET_KEY'] = os.environ.get('WTF_CSRF_SECRET_KEY', 'csrf-key-for-development-only')
    
    # Initialize CSRF protection
    csrf.init_app(app)
    
    # Add CSRF token to template context
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=csrf._get_token)
    
    # Initialize Firebase Admin SDK
    firebase_creds = os.environ.get('FIREBASE_ADMIN_CREDENTIALS_BASE64')
    if firebase_creds:
        try:
            cred_json = base64.b64decode(firebase_creds).decode('utf-8')
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            
            # Initialize Firebase with Auth configuration
            firebase_app = initialize_app(cred, {
                'projectId': cred_dict['project_id'],
                'storageBucket': f"{cred_dict['project_id']}.appspot.com",
                'databaseURL': f"https://{cred_dict['project_id']}.firebaseio.com",
                'databaseAuthVariableOverride': {
                    'uid': 'attendance-system-server'
                }
            })
            
            # Initialize Firestore
            db = firestore.client()
            app.db = db
            
            app.logger.info("Firebase Admin SDK initialized successfully")
        except Exception as e:
            app.logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise
    
    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Initialize caching
    init_cache(app)
    
    # Initialize rate limiting
    init_limiter(app)
    
    # Initialize custom Jinja2 filters
    init_filters(app)
    
    # Register blueprints
    from app.routes import auth_bp, main_bp, admin_bp, ai_bp, recognition_bp, attendance_bp, chat_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(recognition_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(monitoring_bp, url_prefix='/monitoring')
    
    # Register error handlers
    register_error_handlers(app)
    
    @app.before_request
    def before_request():
        """Set up request context"""
        if not hasattr(g, 'db_service'):
            g.db_service = DatabaseService()
    
    # Set up logging
    if not app.debug and not app.testing:
        # Ensure logs directory exists
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # Set up file handler
        file_handler = RotatingFileHandler(
            app.config.get('LOG_FILE', 'logs/attendanceai.log'),
            maxBytes=app.config.get('LOG_MAX_BYTES', 10240),
            backupCount=app.config.get('LOG_BACKUP_COUNT', 10)
        )
        
        file_handler.setFormatter(logging.Formatter(
            app.config.get(
                'LOG_FORMAT',
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            )
        ))
        
        file_handler.setLevel(app.config.get('LOG_LEVEL', logging.INFO))
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(app.config.get('LOG_LEVEL', logging.INFO))
        app.logger.info('AttendanceAI startup')
    
    # Add security headers
    @app.after_request
    def add_security_headers(response):
        """Add security headers to response"""
        for header, value in app.config.get('SECURITY_HEADERS', {}).items():
            response.headers[header] = value
        return response
    
    return app 