"""
Facial Recognition Attendance System
----------------------------------

A modern attendance management system using facial recognition,
powered by AWS Rekognition, Firebase, and Gemini AI.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_login import LoginManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_session import Session
from celery import Celery

# Initialize extensions
login_manager = LoginManager()
cors = CORS()
limiter = Limiter(key_func=get_remote_address)
cache = Cache()
session = Session()
celery = Celery()

# Import services
from .services.face_service import FaceService
from .services.db_service import DatabaseService
from .services.ai_service import AIService

# Global service instances
face_service = None
db_service = None
ai_service = None

def init_services(app):
    """Initialize services with application context"""
    global face_service, db_service, ai_service
    
    services_initialized = True
    
    try:
        db_service = DatabaseService()
        app.logger.info("Database service initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize database service: {str(e)}")
        services_initialized = False

    try:
        face_service = FaceService()
        app.logger.info("Face service initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize face service: {str(e)}")
        services_initialized = False

    try:
        ai_service = AIService()
        app.logger.info("AI service initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize AI service: {str(e)}")
        services_initialized = False

    if not services_initialized:
        app.logger.warning("Some services failed to initialize. Application may have limited functionality.")

def create_default_admin(app):
    """Create default admin user if it doesn't exist"""
    from .models.user import User
    from .constants import UserRole, UserStatus
    
    # Check if admin exists
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        # Create admin user
        admin = User(
            email='admin@example.com',
            password='admin123',  # This will be hashed automatically
            first_name='Admin',
            last_name='User',
            role=UserRole.ADMIN.value,
            status=UserStatus.ACTIVE.value,
            email_verified=True
        )
        
        # Add to database
        db.session.add(admin)
        db.session.commit()
        app.logger.info("Default admin user created successfully!")

def create_app(config_name=None):
    """Create and configure the Flask application"""
    app = Flask(__name__)

    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(f'app.config.{config_name.capitalize()}Config')

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize extensions
    login_manager.init_app(app)
    cors.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
    session.init_app(app)

    # Configure Celery
    celery.conf.update(app.config)
    
    # Initialize services within application context
    with app.app_context():
        init_services(app)
        create_default_admin(app)  # Create default admin user

    # Configure logging
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')

        # Create file handler
        file_handler = RotatingFileHandler(
            'logs/attendance.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Attendance System startup')

    # Register blueprints
    from .routes import (
        index,
        auth,
        user,
        subject,
        attendance,
        recognition,
        chat
    )

    app.register_blueprint(index.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(user.bp)
    app.register_blueprint(subject.bp)
    app.register_blueprint(attendance.bp)
    app.register_blueprint(recognition.bp)
    app.register_blueprint(chat.bp)

    # Configure user loader
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID"""
        from .models.user import User
        return User.get_by_id(user_id)

    # Configure error handlers
    @app.errorhandler(400)
    def bad_request_error(error):
        """Handle 400 Bad Request errors"""
        return {
            'error': 'Bad Request',
            'message': str(error)
        }, 400

    @app.errorhandler(401)
    def unauthorized_error(error):
        """Handle 401 Unauthorized errors"""
        return {
            'error': 'Unauthorized',
            'message': 'Authentication required'
        }, 401

    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 Forbidden errors"""
        return {
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource'
        }, 403

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors"""
        return {
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }, 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error"""
        app.logger.error(f'Server Error: {str(error)}')
        return {
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }, 500

    return app 