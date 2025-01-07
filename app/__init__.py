from flask import Flask, render_template
from flask_login import LoginManager
from flask_cors import CORS
from config import Config
from app.models.user import User
from app.services.db_service import init_db

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    CORS(app)
    login_manager.init_app(app)
    init_db(app)
    
    # Register blueprints
    from app.routes import auth, admin, teacher, student, chat
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(teacher.bp)
    app.register_blueprint(student.bp)
    app.register_blueprint(chat.bp)
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
        
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html'), 500
        
    return app 