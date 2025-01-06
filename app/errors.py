import traceback
from typing import Tuple, Union, Dict, Any
from flask import render_template, request, jsonify
from werkzeug.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)

def init_error_handlers(app):
    """Initialize error handlers for the application"""
    
    def wants_json_response() -> bool:
        """Check if the request wants a JSON response"""
        return request.accept_mimetypes.best == 'application/json'
    
    def log_error(error: Exception) -> None:
        """Log error details"""
        logger.error(f"Error occurred: {str(error)}")
        logger.error(f"Request URL: {request.url}")
        logger.error(f"Request Method: {request.method}")
        logger.error(f"Request Headers: {dict(request.headers)}")
        logger.error(f"Request Args: {dict(request.args)}")
        if request.is_json:
            logger.error(f"Request JSON: {request.get_json()}")
        logger.error(f"Traceback: {''.join(traceback.format_tb(error.__traceback__))}")
    
    @app.errorhandler(400)
    def bad_request_error(error) -> Tuple[Union[str, Dict[str, Any]], int]:
        """Handle 400 Bad Request errors"""
        log_error(error)
        if wants_json_response():
            return jsonify({
                'error': 'Bad Request',
                'message': str(error.description if isinstance(error, HTTPException) else error)
            }), 400
        return render_template('errors/error.html', error={
            'code': 400,
            'name': 'Bad Request',
            'description': 'The server could not understand your request. Please check your input and try again.'
        }), 400
    
    @app.errorhandler(401)
    def unauthorized_error(error) -> Tuple[Union[str, Dict[str, Any]], int]:
        """Handle 401 Unauthorized errors"""
        log_error(error)
        if wants_json_response():
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Authentication is required to access this resource'
            }), 401
        return render_template('errors/error.html', error={
            'code': 401,
            'name': 'Unauthorized',
            'description': 'You need to log in to access this page.'
        }), 401
    
    @app.errorhandler(403)
    def forbidden_error(error) -> Tuple[Union[str, Dict[str, Any]], int]:
        """Handle 403 Forbidden errors"""
        log_error(error)
        if wants_json_response():
            return jsonify({
                'error': 'Forbidden',
                'message': 'You do not have permission to access this resource'
            }), 403
        return render_template('errors/error.html', error={
            'code': 403,
            'name': 'Forbidden',
            'description': 'You do not have permission to access this resource. If you believe this is a mistake, please contact your administrator.'
        }), 403
    
    @app.errorhandler(404)
    def not_found_error(error) -> Tuple[Union[str, Dict[str, Any]], int]:
        """Handle 404 Not Found errors"""
        log_error(error)
        if wants_json_response():
            return jsonify({
                'error': 'Not Found',
                'message': 'The requested resource was not found'
            }), 404
        return render_template('errors/error.html', error={
            'code': 404,
            'name': 'Page Not Found',
            'description': 'The page you are looking for might have been removed, had its name changed, or is temporarily unavailable.'
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed_error(error) -> Tuple[Union[str, Dict[str, Any]], int]:
        """Handle 405 Method Not Allowed errors"""
        log_error(error)
        if wants_json_response():
            return jsonify({
                'error': 'Method Not Allowed',
                'message': f'The {request.method} method is not allowed for this endpoint'
            }), 405
        return render_template('errors/error.html', error={
            'code': 405,
            'name': 'Method Not Allowed',
            'description': f'The {request.method} method is not allowed for this endpoint.'
        }), 405
    
    @app.errorhandler(429)
    def too_many_requests_error(error) -> Tuple[Union[str, Dict[str, Any]], int]:
        """Handle 429 Too Many Requests errors"""
        log_error(error)
        if wants_json_response():
            return jsonify({
                'error': 'Too Many Requests',
                'message': 'You have exceeded the rate limit. Please try again later.'
            }), 429
        return render_template('errors/error.html', error={
            'code': 429,
            'name': 'Too Many Requests',
            'description': 'You have made too many requests. Please wait a while before trying again.'
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error) -> Tuple[Union[str, Dict[str, Any]], int]:
        """Handle 500 Internal Server Error"""
        log_error(error)
        if wants_json_response():
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            }), 500
        return render_template('errors/error.html', error={
            'code': 500,
            'name': 'Internal Server Error',
            'description': 'Something went wrong on our end. Please try again later.'
        }), 500
    
    @app.errorhandler(503)
    def service_unavailable_error(error) -> Tuple[Union[str, Dict[str, Any]], int]:
        """Handle 503 Service Unavailable errors"""
        log_error(error)
        if wants_json_response():
            return jsonify({
                'error': 'Service Unavailable',
                'message': 'The service is temporarily unavailable'
            }), 503
        return render_template('errors/error.html', error={
            'code': 503,
            'name': 'Service Unavailable',
            'description': 'The service is temporarily unavailable. Please try again later.'
        }), 503
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error) -> Tuple[Union[str, Dict[str, Any]], int]:
        """Handle unexpected errors"""
        log_error(error)
        if wants_json_response():
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            }), 500
        return render_template('errors/error.html', error={
            'code': 500,
            'name': 'Internal Server Error',
            'description': 'An unexpected error occurred. Our team has been notified.'
        }), 500 