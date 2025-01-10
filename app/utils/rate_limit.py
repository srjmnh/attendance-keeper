"""Rate limiting utilities for the application."""
from flask import request, current_app, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
from flask_login import current_user

def get_user_identifier():
    """Get user identifier for rate limiting."""
    if hasattr(current_user, 'id'):
        return str(current_user.id)
    return get_remote_address()

limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=["100 per hour"]
)

def init_limiter(app):
    """Initialize rate limiter with the application."""
    limiter.init_app(app)
    return limiter

def rate_limit(limits=None, key_func=None):
    """Custom rate limit decorator with dynamic limits."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get user role for dynamic rate limiting
            user_role = getattr(current_user, 'role', 'anonymous')
            
            # Define role-based limits
            role_limits = {
                'admin': "1000 per hour",
                'teacher': "500 per hour",
                'student': "200 per hour",
                'anonymous': "50 per hour"
            }
            
            # Use provided limits or get from role
            actual_limits = limits or [role_limits.get(user_role, role_limits['anonymous'])]
            
            # Store rate limit info in g for logging
            g.rate_limit_info = {
                'role': user_role,
                'limits': actual_limits
            }
            
            # Apply rate limiting
            limiter.limit(
                actual_limits,
                key_func=key_func or get_user_identifier
            )(f)(*args, **kwargs)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, limit):
        self.limit = limit
        super().__init__(f"Rate limit exceeded: {limit}")

def api_rate_limit(limits=None):
    """Rate limit decorator specifically for API endpoints."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Default API limits
            api_limits = limits or ["5 per second", "300 per hour"]
            
            # Check if request is from API
            if request.is_json:
                try:
                    for limit in api_limits:
                        limiter.limit(limit)(f)(*args, **kwargs)
                except Exception as e:
                    current_app.logger.warning(
                        f"Rate limit exceeded for API request: {str(e)}"
                    )
                    raise RateLimitExceeded(api_limits)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def dynamic_rate_limit(func=None, **options):
    """Dynamic rate limit based on user role and endpoint type."""
    if func is None:
        return lambda f: dynamic_rate_limit(f, **options)
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get user role
        user_role = getattr(current_user, 'role', 'anonymous')
        
        # Define base limits
        base_limits = {
            'admin': {
                'api': ["10 per second", "1000 per hour"],
                'web': ["1000 per hour"]
            },
            'teacher': {
                'api': ["5 per second", "500 per hour"],
                'web': ["500 per hour"]
            },
            'student': {
                'api': ["2 per second", "200 per hour"],
                'web': ["200 per hour"]
            },
            'anonymous': {
                'api': ["1 per second", "50 per hour"],
                'web': ["50 per hour"]
            }
        }
        
        # Determine request type
        request_type = 'api' if request.is_json else 'web'
        
        # Get appropriate limits
        role_limits = base_limits.get(user_role, base_limits['anonymous'])
        actual_limits = role_limits[request_type]
        
        # Store rate limit info in g for logging
        g.rate_limit_info = {
            'role': user_role,
            'type': request_type,
            'limits': actual_limits
        }
        
        try:
            # Apply rate limiting
            for limit in actual_limits:
                limiter.limit(limit)(func)(*args, **kwargs)
        except Exception as e:
            current_app.logger.warning(
                f"Rate limit exceeded for {request_type} request: {str(e)}"
            )
            raise RateLimitExceeded(actual_limits)
        
        return func(*args, **kwargs)
    
    return wrapper 