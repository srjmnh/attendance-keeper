import os
from flask import Flask, render_template
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
limiter = Limiter(key_func=get_remote_address)

def create_app():
    # Initialize Flask app
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('app.config.Config')
    
    # Enable CORS
    CORS(app)
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.user import user_bp
    from app.routes.subject import subject_bp
    from app.routes.attendance import attendance_bp
    from app.routes.recognition import recognition_bp
    from app.routes.chat import chat_bp
    from app.routes.report import report_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(subject_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(recognition_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Set up logging
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # Set up file handler
        file_handler = RotatingFileHandler('logs/attendance.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Attendance System startup')
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/error.html', error={
            'code': 404,
            'name': 'Page Not Found',
            'description': 'The page you are looking for might have been removed, had its name changed, or is temporarily unavailable.'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/error.html', error={
            'code': 500,
            'name': 'Internal Server Error',
            'description': 'Something went wrong on our end. Please try again later.'
        }), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/error.html', error={
            'code': 403,
            'name': 'Forbidden',
            'description': 'You do not have permission to access this resource.'
        }), 403

    # Register shell context
    @app.shell_context_processor
    def make_shell_context():
        return {
            'db': db,
            'User': User,
            'Subject': Subject,
            'Attendance': Attendance,
            'Department': Department
        }
    
    # Import models
    from app.models.user import User
    from app.models.subject import Subject
    from app.models.attendance import Attendance
    from app.models.department import Department
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)