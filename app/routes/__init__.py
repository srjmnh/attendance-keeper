"""
Routes Package
------------

This package contains the route blueprints that handle
HTTP requests and define the API endpoints.

Blueprints:
- index: Main application routes
- auth: Authentication routes
- user: User management routes
- subject: Subject management routes
- attendance: Attendance management routes
- recognition: Face recognition routes
- chat: AI chat routes
"""

from .index import bp as index_bp
from .auth import bp as auth_bp
from .user import bp as user_bp
from .subject import bp as subject_bp
from .attendance import bp as attendance_bp
from .recognition import bp as recognition_bp
from .chat import bp as chat_bp

__all__ = [
    'index_bp',
    'auth_bp',
    'user_bp',
    'subject_bp',
    'attendance_bp',
    'recognition_bp',
    'chat_bp'
] 