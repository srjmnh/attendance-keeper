"""Caching service for the application."""
from flask_caching import Cache
from functools import wraps
from flask import current_app
import threading

cache = Cache()
_cache_lock = threading.Lock()

def init_cache(app):
    """Initialize the cache with the application."""
    with _cache_lock:
        cache_config = {
            'CACHE_TYPE': app.config.get('CACHE_TYPE', 'simple'),
            'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_DEFAULT_TIMEOUT', 300),
        }
        
        if app.config.get('CACHE_TYPE') == 'redis':
            cache_config.update({
                'CACHE_REDIS_URL': app.config.get('CACHE_REDIS_URL'),
            })
        
        if not hasattr(app, '_cache_initialized'):
            cache.init_app(app, config=cache_config)
            app._cache_initialized = True
        
        return cache

def cached_with_key(key_prefix, timeout=None):
    """Custom caching decorator with dynamic key generation."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = f"{key_prefix}:{':'.join(str(arg) for arg in args)}"
            if kwargs:
                cache_key += f":{':'.join(f'{k}={v}' for k, v in sorted(kwargs.items()))}"
            
            # Try to get from cache
            rv = cache.get(cache_key)
            if rv is not None:
                current_app.logger.debug(f"Cache hit for key: {cache_key}")
                return rv
            
            # If not in cache, compute and store
            rv = f(*args, **kwargs)
            cache.set(cache_key, rv, timeout=timeout)
            current_app.logger.debug(f"Cache miss for key: {cache_key}")
            return rv
        return decorated_function
    return decorator

def invalidate_cache(pattern):
    """Invalidate cache keys matching the pattern."""
    if hasattr(cache, 'delete_memoized'):
        cache.delete_memoized(pattern)
    else:
        # For simple cache, we can't do pattern matching
        cache.clear()

class CacheService:
    """Service for managing application caching."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize cache service."""
        if not hasattr(self, 'initialized'):
            self.initialized = True
    
    @staticmethod
    def cache_user(user_id, user_data, timeout=300):
        """Cache user data."""
        key = f"user:{user_id}"
        cache.set(key, user_data, timeout=timeout)
    
    @staticmethod
    def get_cached_user(user_id):
        """Get cached user data."""
        return cache.get(f"user:{user_id}")
    
    @staticmethod
    def cache_attendance(date, class_id, attendance_data, timeout=3600):
        """Cache attendance data."""
        key = f"attendance:{date}:{class_id}"
        cache.set(key, attendance_data, timeout=timeout)
    
    @staticmethod
    def get_cached_attendance(date, class_id):
        """Get cached attendance data."""
        return cache.get(f"attendance:{date}:{class_id}")
    
    @staticmethod
    def cache_subject_list(timeout=3600):
        """Decorator for caching subject lists."""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                key = "subject_list"
                result = cache.get(key)
                if result is None:
                    result = f(*args, **kwargs)
                    cache.set(key, result, timeout=timeout)
                return result
            return decorated_function
        return decorator
    
    @staticmethod
    def invalidate_user_cache(user_id):
        """Invalidate user cache."""
        cache.delete(f"user:{user_id}")
    
    @staticmethod
    def invalidate_attendance_cache(date, class_id):
        """Invalidate attendance cache."""
        cache.delete(f"attendance:{date}:{class_id}")
    
    @staticmethod
    def invalidate_subject_list():
        """Invalidate subject list cache."""
        cache.delete("subject_list") 