import functools
from typing import Callable, List, Optional, Any, Union
from flask import request, current_app, jsonify, abort
from flask_login import current_user
import time
import logging
from datetime import datetime, timedelta
from werkzeug.exceptions import BadRequest, Unauthorized, Forbidden, TooManyRequests
import jwt
from redis import Redis
from app.utils import verify_token

logger = logging.getLogger(__name__)

def login_required(f: Callable) -> Callable:
    """Decorator to require login for a route"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json:
                return jsonify({'error': 'Unauthorized', 'message': 'Login required'}), 401
            return current_app.login_manager.unauthorized()
        return f(*args, **kwargs)
    return decorated_function

def roles_required(*roles: str) -> Callable:
    """Decorator to require specific roles for a route"""
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                raise Unauthorized('Login required')
            if not current_user.role in roles:
                raise Forbidden('Insufficient permissions')
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f: Callable) -> Callable:
    """Decorator to require admin role for a route"""
    return roles_required('admin')(f)

def teacher_required(f: Callable) -> Callable:
    """Decorator to require teacher role for a route"""
    return roles_required('teacher', 'admin')(f)

def rate_limit(limit: int, per: int = 60) -> Callable:
    """
    Rate limiting decorator using Redis
    :param limit: Number of allowed requests
    :param per: Time window in seconds
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(current_app, 'redis'):
                return f(*args, **kwargs)
            
            key = f"rate_limit:{request.remote_addr}:{request.endpoint}"
            try:
                redis_client: Redis = current_app.redis
                pipe = redis_client.pipeline()
                now = time.time()
                pipe.zremrangebyscore(key, 0, now - per)
                pipe.zadd(key, {str(now): now})
                pipe.zcard(key)
                pipe.expire(key, per)
                _, _, count, _ = pipe.execute()
                
                if count > limit:
                    raise TooManyRequests(
                        f"Rate limit exceeded. Try again in {per} seconds."
                    )
                
                return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"Rate limiting error: {str(e)}")
                return f(*args, **kwargs)
        return decorated_function
    return decorator

def validate_json(*required_fields: str) -> Callable:
    """
    Decorator to validate JSON payload
    :param required_fields: List of required fields in the JSON payload
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                raise BadRequest('Content-Type must be application/json')
            
            data = request.get_json()
            if not data:
                raise BadRequest('No JSON data provided')
            
            missing_fields = [
                field for field in required_fields
                if field not in data or data[field] is None
            ]
            
            if missing_fields:
                raise BadRequest(
                    f"Missing required fields: {', '.join(missing_fields)}"
                )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def cache_control(*directives: str) -> Callable:
    """
    Decorator to set Cache-Control header
    :param directives: Cache-Control directives
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)
            if isinstance(response, tuple):
                response, status_code = response
            else:
                status_code = 200
            
            if isinstance(response, (dict, list)):
                response = jsonify(response)
            
            response.headers['Cache-Control'] = ', '.join(directives)
            return response, status_code
        return decorated_function
    return decorator

def jwt_required(f: Callable) -> Callable:
    """Decorator to require JWT token for a route"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            raise Unauthorized('Missing Authorization header')
        
        try:
            token_type, token = auth_header.split()
            if token_type.lower() != 'bearer':
                raise Unauthorized('Invalid token type')
            
            payload = verify_token(token)
            if not payload:
                raise Unauthorized('Invalid or expired token')
            
            return f(*args, **kwargs)
        except ValueError:
            raise Unauthorized('Invalid Authorization header format')
    return decorated_function

def validate_file_upload(*allowed_extensions: str) -> Callable:
    """
    Decorator to validate file uploads
    :param allowed_extensions: List of allowed file extensions
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if 'file' not in request.files:
                raise BadRequest('No file uploaded')
            
            file = request.files['file']
            if not file.filename:
                raise BadRequest('No file selected')
            
            ext = file.filename.rsplit('.', 1)[1].lower() \
                if '.' in file.filename else ''
            
            if not allowed_extensions or ext not in allowed_extensions:
                raise BadRequest(
                    f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
                )
            
            max_size = current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)
            if request.content_length > max_size:
                raise BadRequest(
                    f"File too large. Maximum size: {max_size // (1024 * 1024)}MB"
                )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_activity(activity_type: str) -> Callable:
    """
    Decorator to log user activity
    :param activity_type: Type of activity being logged
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                status = 'success'
            except Exception as e:
                status = 'error'
                logger.error(f"Error in {activity_type}: {str(e)}")
                raise
            finally:
                duration = time.time() - start_time
                logger.info(
                    f"Activity: {activity_type}, "
                    f"User: {current_user.id if current_user.is_authenticated else 'anonymous'}, "
                    f"Status: {status}, "
                    f"Duration: {duration:.2f}s, "
                    f"IP: {request.remote_addr}, "
                    f"URL: {request.url}"
                )
            return result
        return decorated_function
    return decorator

def require_params(*params: str) -> Callable:
    """
    Decorator to require specific URL parameters
    :param params: Required parameter names
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            missing_params = [
                param for param in params
                if param not in request.args
            ]
            if missing_params:
                raise BadRequest(
                    f"Missing required parameters: {', '.join(missing_params)}"
                )
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def async_task(f: Callable) -> Callable:
    """Decorator to run a function asynchronously"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        from threading import Thread
        thread = Thread(target=f, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread
    return decorated_function

def retry(max_retries: int = 3, delay: float = 1.0) -> Callable:
    """
    Decorator to retry a function on failure
    :param max_retries: Maximum number of retries
    :param delay: Delay between retries in seconds
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(
                            f"Max retries ({max_retries}) reached for {f.__name__}"
                        )
                        raise
                    logger.warning(
                        f"Retry {retries}/{max_retries} for {f.__name__}: {str(e)}"
                    )
                    time.sleep(delay)
        return decorated_function
    return decorator 