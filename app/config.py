import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

class Config:
    # AWS Configuration
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_REGION = os.getenv('AWS_REGION')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    # Azure Configuration
    AZURE_API_KEY = os.getenv('AZURE_API_KEY')
    AZURE_FACE_ENDPOINT = os.getenv('AZURE_FACE_ENDPOINT')
    
    # Admin Configuration
    DEFAULT_ADMIN_USERNAME = os.getenv('DEFAULT_ADMIN_USERNAME')
    
    # Firebase Configuration
    FIREBASE_ADMIN_CREDENTIALS_BASE64 = os.getenv('FIREBASE_ADMIN_CREDENTIALS_BASE64')
    
    # API Keys
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    HF_API_KEY = os.getenv('HF_API_KEY')
    
    # Server Configuration
    PORT = int(os.getenv('PORT', 5000))
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes
    
    # Cache Configuration
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Rate Limiting
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URL = "memory://"
    
    # CORS Configuration
    CORS_ORIGINS = ['*']  # Update with specific origins in production
    
    @staticmethod
    def init_app(app):
        # Create upload folder if it doesn't exist
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        
        # Additional initialization can be added here
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False
    # Add production-specific configurations here

class TestingConfig(Config):
    TESTING = True
    # Add testing-specific configurations here

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 