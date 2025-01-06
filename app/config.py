import os
from datetime import timedelta

class Config:
    """Base configuration class"""
    
    # Basic Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'
    TESTING = False
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///attendance.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = DEBUG
    
    # AWS configuration for facial recognition
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
    AWS_COLLECTION_ID = os.environ.get('AWS_COLLECTION_ID', 'attendance-faces')
    AWS_BUCKET_NAME = os.environ.get('AWS_BUCKET_NAME', 'attendance-images')
    
    # Firebase configuration
    FIREBASE_CREDENTIALS = os.environ.get('FIREBASE_CREDENTIALS_PATH')
    FIREBASE_DATABASE_URL = os.environ.get('FIREBASE_DATABASE_URL')
    
    # Google Cloud configuration for Gemini AI
    GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT')
    GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    
    # Mail configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File upload configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    
    # Rate limiting configuration
    RATELIMIT_DEFAULT = "100 per minute"
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    
    # Security configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    
    # Password hashing configuration
    BCRYPT_LOG_ROUNDS = 12
    
    # JWT configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Cache configuration
    CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')
    CACHE_REDIS_URL = os.environ.get('REDIS_URL')
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Logging configuration
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT', 'false').lower() in ['true', 'on', '1']
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # API configuration
    API_TITLE = 'Attendance System API'
    API_VERSION = '1.0'
    OPENAPI_VERSION = '3.0.2'
    OPENAPI_URL_PREFIX = '/api/docs'
    OPENAPI_SWAGGER_UI_PATH = '/swagger'
    OPENAPI_SWAGGER_UI_URL = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist/'
    
    # Face recognition configuration
    FACE_DETECTION_CONFIDENCE = 0.8
    FACE_MATCHING_THRESHOLD = 0.8
    MAX_FACES_PER_IMAGE = 10
    
    # Attendance configuration
    ATTENDANCE_WINDOW_MINUTES = 15  # Time window for marking attendance
    LATE_THRESHOLD_MINUTES = 5  # Time after which attendance is marked as late
    MIN_ATTENDANCE_PERCENTAGE = 75  # Minimum required attendance percentage
    
    # Report generation configuration
    REPORT_FORMATS = ['pdf', 'excel', 'csv']
    REPORT_TIMEZONE = 'UTC'
    
    # Notification configuration
    ENABLE_EMAIL_NOTIFICATIONS = True
    ENABLE_PUSH_NOTIFICATIONS = False
    
    @staticmethod
    def init_app(app):
        """Initialize application with this configuration"""
        # Create upload folder if it doesn't exist
        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)
        
        # Set up logging
        if not app.debug and not app.testing:
            if Config.LOG_TO_STDOUT:
                import logging
                from logging import StreamHandler
                stream_handler = StreamHandler()
                stream_handler.setLevel(logging.INFO)
                app.logger.addHandler(stream_handler)
            else:
                if not os.path.exists('logs'):
                    os.mkdir('logs')
                from logging.handlers import RotatingFileHandler
                file_handler = RotatingFileHandler(
                    'logs/attendance.log',
                    maxBytes=10240,
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

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///attendance_dev.db'
    SESSION_COOKIE_SECURE = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///attendance_test.db'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    @classmethod
    def init_app(cls, app):
        """Production-specific initialization"""
        Config.init_app(app)
        
        # Set up production logging
        import logging
        from logging.handlers import SMTPHandler
        credentials = None
        secure = None
        
        if getattr(cls, 'MAIL_USERNAME', None) is not None:
            credentials = (cls.MAIL_USERNAME, cls.MAIL_PASSWORD)
            if getattr(cls, 'MAIL_USE_TLS', None):
                secure = ()
        
        mail_handler = SMTPHandler(
            mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT),
            fromaddr=cls.MAIL_DEFAULT_SENDER,
            toaddrs=[cls.MAIL_DEFAULT_SENDER],
            subject='Attendance System Error',
            credentials=credentials,
            secure=secure
        )
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
} 