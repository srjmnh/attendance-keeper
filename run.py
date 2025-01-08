from flask import Flask
from flask_login import LoginManager
from app.services.db_service import DatabaseService
from app.routes import admin, auth, main, ai, attendance, recognition
import os
import boto3

COLLECTION_ID = "students"  # Hardcode the collection ID to match the example code

def create_collection_if_not_exists(rekognition_client, collection_id):
    """Create AWS Rekognition collection if it doesn't exist"""
    try:
        rekognition_client.create_collection(CollectionId=collection_id)
        print(f"Collection '{collection_id}' created.")
    except rekognition_client.exceptions.ResourceAlreadyExistsException:
        print(f"Collection '{collection_id}' already exists.")
    except Exception as e:
        print(f"Error creating collection: {str(e)}")

def create_app():
    app = Flask(__name__,
                template_folder='app/templates',
                static_folder='app/static')
    
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
    
    # Initialize Firebase Admin
    db = DatabaseService()
    app.db = db.get_db()
    
    # Initialize AWS Rekognition
    app.rekognition = boto3.client(
        'rekognition',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_REGION', 'us-east-1')
    )
    
    # Create collection if it doesn't exist
    create_collection_if_not_exists(app.rekognition, COLLECTION_ID)
    
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