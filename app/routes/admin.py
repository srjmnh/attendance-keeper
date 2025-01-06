from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from ..models.user import User
from functools import wraps
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/manage_users')
@login_required
@admin_required
def manage_users():
    """Show user management page"""
    users = User.get_all()
    return render_template('admin/manage_users.html', users=users)

@bp.route('/users/<user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    """Update user details"""
    try:
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Validate role if provided
        if 'role' in data and data['role'] not in ['admin', 'teacher', 'student']:
            return jsonify({'error': 'Invalid role'}), 400

        # Update user
        if user.update(data):
            return jsonify({
                'message': 'User updated successfully',
                'user': user.to_dict()
            })
        return jsonify({'error': 'Failed to update user'}), 500

    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/users/<user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete user"""
    try:
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if user.delete():
            return jsonify({
                'message': 'User deleted successfully',
                'user_id': user_id
            })
        return jsonify({'error': 'Failed to delete user'}), 500

    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/users/<user_id>/activate', methods=['POST'])
@login_required
@admin_required
def activate_user(user_id):
    """Activate user"""
    try:
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if user.activate():
            return jsonify({
                'message': 'User activated successfully',
                'user': user.to_dict()
            })
        return jsonify({'error': 'Failed to activate user'}), 500

    except Exception as e:
        logger.error(f"Error activating user: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/users/<user_id>/deactivate', methods=['POST'])
@login_required
@admin_required
def deactivate_user(user_id):
    """Deactivate user"""
    try:
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        if user.deactivate():
            return jsonify({
                'message': 'User deactivated successfully',
                'user': user.to_dict()
            })
        return jsonify({'error': 'Failed to deactivate user'}), 500

    except Exception as e:
        logger.error(f"Error deactivating user: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 