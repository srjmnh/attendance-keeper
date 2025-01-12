from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from app.models.approval import ApprovalRequest, ApprovalType
from app.services.approval_service import ApprovalService
from app.utils.decorators import admin_required, teacher_required
from functools import wraps

approval_bp = Blueprint('approval', __name__)

def init_service(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app import get_db, get_notification_service
        approval_service = ApprovalService(get_db(), get_notification_service())
        return f(approval_service, *args, **kwargs)
    return decorated_function

@approval_bp.route('/approvals/pending')
@login_required
@admin_required
@init_service
async def pending_approvals(approval_service):
    """View pending approval requests."""
    requests = await approval_service.get_pending_requests()
    return render_template('approval/pending.html', requests=requests)

@approval_bp.route('/approvals/my-requests')
@login_required
@init_service
async def my_requests(approval_service):
    """View user's own requests."""
    requests = await approval_service.get_user_requests(current_user.id)
    return render_template('approval/my_requests.html', requests=requests)

@approval_bp.route('/approvals/<request_id>')
@login_required
@init_service
async def view_request(approval_service, request_id):
    """View a specific approval request."""
    request = await approval_service.get_request(request_id)
    if not request:
        return jsonify({"error": "Request not found"}), 404
    
    # Check if user has permission to view this request
    if not current_user.is_admin and request.requestor_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403
        
    return render_template('approval/view_request.html', request=request)

@approval_bp.route('/api/approvals/<request_id>/approve', methods=['POST'])
@login_required
@admin_required
@init_service
async def approve_request(approval_service, request_id):
    """Approve a request."""
    data = request.get_json()
    comment = data.get('comment')
    
    try:
        await approval_service.approve_request(request_id, current_user.id, comment)
        return jsonify({"message": "Request approved successfully"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

@approval_bp.route('/api/approvals/<request_id>/reject', methods=['POST'])
@login_required
@admin_required
@init_service
async def reject_request(approval_service, request_id):
    """Reject a request."""
    data = request.get_json()
    comment = data.get('comment')
    
    try:
        await approval_service.reject_request(request_id, current_user.id, comment)
        return jsonify({"message": "Request rejected successfully"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

@approval_bp.route('/api/approvals/<request_id>/comment', methods=['POST'])
@login_required
@init_service
async def add_comment(approval_service, request_id):
    """Add a comment to a request."""
    data = request.get_json()
    comment = data.get('comment')
    
    if not comment:
        return jsonify({"error": "Comment is required"}), 400
        
    try:
        await approval_service.add_comment(request_id, current_user.id, comment)
        return jsonify({"message": "Comment added successfully"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

# Teacher-specific routes
@approval_bp.route('/api/students/<student_id>/edit', methods=['POST'])
@login_required
@teacher_required
@init_service
async def request_student_edit(approval_service, student_id):
    """Request to edit student information."""
    data = request.get_json()
    
    # Create approval request
    approval_request = ApprovalRequest(
        ApprovalType.STUDENT_EDIT,
        current_user.id,
        {
            "student_id": student_id,
            "changes": data.get('changes'),
            "reason": data.get('reason')
        }
    )
    
    request_id = await approval_service.create_request(approval_request)
    return jsonify({
        "message": "Edit request submitted successfully",
        "request_id": request_id
    }) 