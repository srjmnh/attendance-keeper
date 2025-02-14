"""Routes package initialization."""
from app.routes.auth import auth_bp
from app.routes.main import main_bp
from app.routes.admin import admin_bp
from app.routes.ai import ai_bp
from app.routes.recognition import recognition_bp
from app.routes.attendance import attendance_bp
from app.routes.chat import chat_bp
from app.routes.teacher import teacher_bp
from app.routes.approval import approval_bp
from app.routes.notification import notification_bp

__all__ = [
    'auth_bp',
    'main_bp',
    'admin_bp',
    'ai_bp',
    'recognition_bp',
    'attendance_bp',
    'chat_bp',
    'teacher_bp',
    'approval_bp',
    'notification_bp'
] 