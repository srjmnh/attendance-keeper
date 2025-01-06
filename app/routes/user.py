from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from ..models.user import User
from ..models.subject import Subject
from .. import db_service

bp = Blueprint('user', __name__, url_prefix='/user')

@bp.route('', methods=['GET'])
@login_required
def get_users():
    """Get users with optional filters"""
    try:
        if not current_user.is_admin and not current_user.is_teacher:
            return jsonify({'error': 'Unauthorized'}), 403

        # Parse query parameters
        role = request.args.get('role')
        subject_id = request.args.get('subject_id')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))

        # Get users based on role and filters
        if current_user.is_teacher:
            if subject_id and subject_id not in current_user.classes:
                return jsonify({'error': 'Unauthorized to view this subject'}), 403
            users = db_service.get_users(
                role='student',
                subject_id=subject_id,
                teacher_classes=current_user.classes
            )
        else:  # Admin
            users = db_service.get_users(role=role, subject_id=subject_id)

        # Paginate results
        total_users = len(users)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_users = users[start_idx:end_idx]

        return jsonify({
            'users': [user.to_dict() for user in paginated_users],
            'total_users': total_users,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_users + per_page - 1) // per_page
        })

    except Exception as e:
        current_app.logger.error(f"Error getting users: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    """Get user details"""
    try:
        # Students can only view their own profile
        if current_user.is_student and user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Teachers can only view their students
        if current_user.is_teacher:
            student_subjects = set(user.classes)
            teacher_subjects = set(current_user.classes)
            if not student_subjects.intersection(teacher_subjects):
                return jsonify({'error': 'Unauthorized'}), 403

        return jsonify(user.to_dict())

    except Exception as e:
        current_app.logger.error(f"Error getting user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('', methods=['POST'])
@login_required
def create_user():
    """Create a new user"""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        required_fields = ['username', 'password', 'name', 'role']
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            return jsonify({
                'error': f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        # Validate role
        if data['role'] not in ['admin', 'teacher', 'student']:
            return jsonify({'error': 'Invalid role'}), 400

        # Hash password
        data['password'] = generate_password_hash(data['password'])

        # Create user
        user = User.create(data)
        if not user:
            return jsonify({'error': 'Username already exists'}), 400

        # Add subjects if provided
        if 'subjects' in data and isinstance(data['subjects'], list):
            for subject_id in data['subjects']:
                subject = Subject.get_by_id(subject_id)
                if subject:
                    user.add_subject(subject_id)

        return jsonify({
            'message': 'User created successfully',
            'user': user.to_dict()
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error creating user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """Update user details"""
    try:
        # Get user
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Check permissions
        if current_user.is_student:
            if user_id != current_user.id:
                return jsonify({'error': 'Unauthorized'}), 403
            allowed_fields = ['name', 'password']
        elif current_user.is_teacher:
            if not user.is_student:
                return jsonify({'error': 'Unauthorized'}), 403
            student_subjects = set(user.classes)
            teacher_subjects = set(current_user.classes)
            if not student_subjects.intersection(teacher_subjects):
                return jsonify({'error': 'Unauthorized'}), 403
            allowed_fields = ['name']
        else:  # Admin
            allowed_fields = ['name', 'password', 'role', 'subjects', 'active']

        # Get update data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Filter allowed fields
        updates = {k: v for k, v in data.items() if k in allowed_fields}
        if not updates:
            return jsonify({'error': 'No valid fields to update'}), 400

        # Hash password if provided
        if 'password' in updates:
            updates['password'] = generate_password_hash(updates['password'])

        # Update user
        if not user.update(updates):
            return jsonify({'error': 'Failed to update user'}), 500

        # Update subjects if provided (admin only)
        if current_user.is_admin and 'subjects' in data:
            if isinstance(data['subjects'], list):
                user.set_subjects(data['subjects'])

        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        })

    except Exception as e:
        current_app.logger.error(f"Error updating user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """Delete a user"""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403

        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Prevent deleting self
        if user_id == current_user.id:
            return jsonify({'error': 'Cannot delete own account'}), 400

        # Delete user
        if not user.delete():
            return jsonify({'error': 'Failed to delete user'}), 500

        return jsonify({'message': 'User deleted successfully'})

    except Exception as e:
        current_app.logger.error(f"Error deleting user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Get current user's profile"""
    try:
        return jsonify(current_user.to_dict())

    except Exception as e:
        current_app.logger.error(f"Error getting profile: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """Update current user's profile"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Students and teachers can only update name and password
        allowed_fields = ['name', 'password']
        updates = {k: v for k, v in data.items() if k in allowed_fields}
        if not updates:
            return jsonify({'error': 'No valid fields to update'}), 400

        # Hash password if provided
        if 'password' in updates:
            updates['password'] = generate_password_hash(updates['password'])

        # Update profile
        if not current_user.update(updates):
            return jsonify({'error': 'Failed to update profile'}), 500

        return jsonify({
            'message': 'Profile updated successfully',
            'user': current_user.to_dict()
        })

    except Exception as e:
        current_app.logger.error(f"Error updating profile: {str(e)}")
        return jsonify({'error': str(e)}), 500 