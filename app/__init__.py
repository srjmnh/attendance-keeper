from flask import Flask
from flask_login import LoginManager
from flask_cors import CORS
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.models.user import User
from app.services.db_service import DatabaseService

# Initialize extensions
login_manager = LoginManager()
cors = CORS()
cache = Cache()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@login_manager.user_loader
def load_user(user_id):
    db = DatabaseService()
    user_data = db.get_user_by_id(user_id)
    return User.from_dict(user_data) if user_data else None

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