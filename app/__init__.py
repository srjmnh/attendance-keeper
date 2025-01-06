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
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_session import Session
from celery import Celery

# Initialize SQLAlchemy
db = SQLAlchemy()
login_manager = LoginManager()

# Initialize extensions
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
    
    try:
        # Check if admin exists
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            # Create admin user
            admin = User(
                email='admin@example.com',
                first_name='Admin',
                last_name='User',
                role='admin',
                status='active',
                email_verified=True
            )
            admin.password = 'admin123'  # This will be hashed by the setter
            
            # Add to database
            db.session.add(admin)
            db.session.commit()
            app.logger.info("Default admin user created successfully!")
    except Exception as e:
        app.logger.error(f"Error creating default admin: {str(e)}")
        # Don't raise the exception, let the app continue without admin user
        pass

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

    # Configure SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    cors.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
    session.init_app(app)

    # Configure Celery
    celery.conf.update(app.config)
    
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

    # Initialize database and services within application context
    with app.app_context():
        try:
            # Create database tables
            db.create_all()
            app.logger.info("Database tables created successfully")
            
            # Create default admin user
            create_default_admin(app)
            
            # Initialize services
            init_services(app)
            
        except Exception as e:
            app.logger.error(f"Error during initialization: {str(e)}")
            # Don't raise the exception, let the app continue with limited functionality
            pass

    return app 