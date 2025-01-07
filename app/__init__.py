from flask import Flask, render_template
from flask_login import LoginManager
from flask_cors import CORS
from config import Config
from app.models.user import User
from app.services.db_service import init_db, DatabaseService

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login"""
    try:
        db = DatabaseService()
        user_data = db.get_user_by_id(user_id)
        if user_data:
            return User.from_dict(user_data)
        return None
    except Exception as e:
        current_app.logger.error(f"Error loading user {user_id}: {str(e)}")
        return None

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    CORS(app)
    login_manager.init_app(app)
    init_db(app)
    
    # Register blueprints
    from app.routes import auth, admin, teacher, student, chat
    app.register_blueprint(auth.auth)
    app.register_blueprint(admin.admin)
    app.register_blueprint(teacher.bp)
    app.register_blueprint(student.bp)
    app.register_blueprint(chat.chat)
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
        
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
        
    return app 