from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.services.notification_service import NotificationService
from functools import wraps

notification_bp = Blueprint('notification', __name__)

def init_service(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app import get_db
        notification_service = NotificationService(get_db())
        return f(notification_service, *args, **kwargs)
    return decorated_function

@notification_bp.route('/api/notifications')
@login_required
@init_service
async def get_notifications(notification_service):
    """Get user's notifications."""
    limit = request.args.get('limit', 50, type=int)
    notifications = await notification_service.get_user_notifications(current_user.id, limit)
    return jsonify([n.to_dict() for n in notifications])

@notification_bp.route('/api/notifications/unread-count')
@login_required
@init_service
async def get_unread_count(notification_service):
    """Get count of unread notifications."""
    count = await notification_service.get_unread_count(current_user.id)
    return jsonify({"count": count})

@notification_bp.route('/api/notifications/<notification_id>/read', methods=['POST'])
@login_required
@init_service
async def mark_as_read(notification_service, notification_id):
    """Mark a notification as read."""
    await notification_service.mark_as_read(notification_id)
    return jsonify({"message": "Notification marked as read"})

@notification_bp.route('/api/notifications/<notification_id>/archive', methods=['POST'])
@login_required
@init_service
async def archive_notification(notification_service, notification_id):
    """Archive a notification."""
    await notification_service.archive_notification(notification_id)
    return jsonify({"message": "Notification archived"})

# Attendance dispute routes
@notification_bp.route('/api/attendance/dispute', methods=['POST'])
@login_required
@init_service
async def file_attendance_dispute(notification_service):
    """File an attendance dispute."""
    data = request.get_json()
    
    # Create dispute record (implement this based on your data model)
    dispute_id = "implement_dispute_creation"
    
    # Get teacher information (implement this based on your data model)
    teacher_id = "implement_get_teacher"
    
    # Notify teacher about the dispute
    student_info = {
        "name": current_user.name,
        "id": current_user.id,
        "class": data.get("class"),
        "date": data.get("date")
    }
    
    await notification_service.notify_dispute_filed(dispute_id, teacher_id, student_info)
    
    return jsonify({
        "message": "Dispute filed successfully",
        "dispute_id": dispute_id
    }) 