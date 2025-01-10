"""Development configuration."""
from app.config import BaseConfig

class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    
    # Override session configuration for development
    SESSION_COOKIE_SECURE = False
    
    # Development-specific settings
    TEMPLATES_AUTO_RELOAD = True
    EXPLAIN_TEMPLATE_LOADING = True
    
    # SQL Alchemy settings (if needed in future)
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    
    # Debug toolbar settings
    DEBUG_TB_ENABLED = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    
    # Development logging
    LOG_LEVEL = 'DEBUG'
    LOG_TO_STDOUT = True 