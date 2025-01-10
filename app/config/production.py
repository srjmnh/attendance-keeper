"""Production configuration."""
from app.config import BaseConfig

class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    
    # Enhanced security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Production logging
    LOG_LEVEL = 'INFO'
    LOG_TO_STDOUT = False
    LOG_TO_FILE = True
    LOG_FILE = 'logs/production.log'
    LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    LOG_MAX_BYTES = 10485760  # 10MB
    LOG_BACKUP_COUNT = 10
    
    # Production security headers
    SECURITY_HEADERS = {
        **BaseConfig.SECURITY_HEADERS,
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';"
    }
    
    # Rate limiting
    RATELIMIT_DEFAULT = "50/minute"
    RATELIMIT_STORAGE_URL = "redis://localhost:6379/0"
    
    # Cache configuration
    CACHE_TYPE = "redis"
    CACHE_REDIS_URL = "redis://localhost:6379/1"
    CACHE_DEFAULT_TIMEOUT = 300 