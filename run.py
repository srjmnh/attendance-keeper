from flask import Flask
from flask_login import LoginManager
from app.services.db_service import DatabaseService
from app.routes import admin, auth, main, ai, attendance, recognition
import os

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
    
    # Initialize Firebase Admin
    db = DatabaseService()
    app.db = db.get_db()
    
    # Initialize Login Manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return db.get_user_by_id(user_id)
    
    # Register blueprints
    app.register_blueprint(admin.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(ai.bp)
    app.register_blueprint(attendance.bp)
    app.register_blueprint(recognition.bp)
    
    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True) 