"""Error handling utilities for the application."""
from flask import jsonify, render_template, request
from werkzeug.http import HTTP_STATUS_CODES

class APIError(Exception):
    """Base API Error class."""
    
    def __init__(self, message, status_code=400, payload=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        """Convert error to dictionary format."""
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['status'] = self.status_code
        rv['error'] = HTTP_STATUS_CODES.get(self.status_code, 'Unknown error')
        return rv

class ValidationError(APIError):
    """Validation error."""
    
    def __init__(self, message):
        super().__init__(message, status_code=422)

class AuthenticationError(APIError):
    """Authentication error."""
    
    def __init__(self, message):
        super().__init__(message, status_code=401)

class AuthorizationError(APIError):
    """Authorization error."""
    
    def __init__(self, message):
        super().__init__(message, status_code=403)

class NotFoundError(APIError):
    """Resource not found error."""
    
    def __init__(self, message):
        super().__init__(message, status_code=404)

class ServiceError(APIError):
    """External service error."""
    
    def __init__(self, message, service_name):
        super().__init__(
            message,
            status_code=503,
            payload={'service': service_name}
        )

def register_error_handlers(app):
    """Register error handlers with the Flask application."""
    
    def handle_api_error(error):
        """Handle API errors."""
        if request.is_json:
            response = jsonify(error.to_dict())
            response.status_code = error.status_code
            return response
        
        return render_template(
            'errors/error.html',
            error=error.to_dict()
        ), error.status_code
    
    def handle_404(error):
        """Handle 404 errors."""
        if request.is_json:
            return jsonify({
                'message': 'Resource not found',
                'status': 404,
                'error': 'Not Found'
            }), 404
        
        return render_template('errors/404.html'), 404
    
    def handle_500(error):
        """Handle 500 errors."""
        app.logger.error(f'Server Error: {error}')
        if request.is_json:
            return jsonify({
                'message': 'Internal server error',
                'status': 500,
                'error': 'Internal Server Error'
            }), 500
        
        return render_template('errors/500.html'), 500
    
    # Register handlers
    app.register_error_handler(APIError, handle_api_error)
    app.register_error_handler(404, handle_404)
    app.register_error_handler(500, handle_500)
    
    return app 