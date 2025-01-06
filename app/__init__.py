from flask import Flask
from flask_login import LoginManager
import firebase_admin
from firebase_admin import credentials
import os
import logging

def create_app(test_config=None):
    """Create and configure the Flask application"""
    app = Flask(__name__)

    # Load default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        AWS_ACCESS_KEY_ID=os.environ.get('AWS_ACCESS_KEY_ID'),
        AWS_SECRET_ACCESS_KEY=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        AWS_REGION=os.environ.get('AWS_REGION', 'us-east-1'),
        COLLECTION_ID=os.environ.get('COLLECTION_ID', 'faces'),
        FACE_MATCH_THRESHOLD=float(os.environ.get('FACE_MATCH_THRESHOLD', '80.0')),
        GEMINI_API_KEY=os.environ.get('GEMINI_API_KEY'),
        FIREBASE_CREDENTIALS=os.environ.get('FIREBASE_CREDENTIALS'),
        UPLOAD_FOLDER=os.path.join(app.instance_path, 'uploads'),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024  # 16MB max file size
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.update(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
        os.makedirs(app.config['UPLOAD_FOLDER'])
    except OSError:
        pass

    # Initialize Firebase Admin SDK
    if not firebase_admin._apps:
        if app.config['FIREBASE_CREDENTIALS']:
            cred = credentials.Certificate(app.config['FIREBASE_CREDENTIALS'])
        else:
            # Use application default credentials
            cred = credentials.ApplicationDefault()
        firebase_admin.initialize_app(cred)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from .models.user import User
        return User.get_by_id(user_id)

    # Register blueprints
    from .routes import auth, recognition, attendance, subjects
    app.register_blueprint(auth.bp, url_prefix='/auth')
    app.register_blueprint(recognition.bp, url_prefix='/recognition')
    app.register_blueprint(attendance.bp, url_prefix='/attendance')
    app.register_blueprint(subjects.bp, url_prefix='/subjects')

    # Configure logging
    if not app.debug:
        logging.basicConfig(level=logging.INFO)
        file_handler = logging.FileHandler(os.path.join(app.instance_path, 'app.log'))
        file_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        ))
        app.logger.addHandler(file_handler)

    # Create default admin user
    with app.app_context():
        from .routes.auth import create_default_admin
        create_default_admin()

    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        return {'status': 'healthy'}, 200

    return app 