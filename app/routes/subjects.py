from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from ..models.subject import Subject
from ..services.ai_service import AIService
from functools import wraps
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('subjects', __name__)

def teacher_required(f):
    """Decorator to require teacher or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or (
            not current_user.is_teacher and not current_user.is_admin
        ):
            return jsonify({'error': 'Teacher or admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/', methods=['POST'])
@login_required
@teacher_required
def create_subject():
    """Create a new subject"""
    try:
        data = request.get_json()
        required_fields = ['name', 'code']
        if not data or not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        # Check if subject code already exists
        existing_subject = Subject.get_by_code(data['code'])
        if existing_subject:
            return jsonify({'error': 'Subject code already exists'}), 400

        # Create subject
        subject = Subject(
            name=data['name'],
            code=data['code'],
            description=data.get('description'),
            teacher_id=current_user.id,
            teacher_name=current_user.username,
            schedule=data.get('schedule', {})
        )
        subject.save()

        return jsonify({
            'message': 'Subject created successfully',
            'subject': subject.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating subject: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/', methods=['GET'])
@login_required
def list_subjects():
    """List subjects based on user role"""
    try:
        include_inactive = request.args.get('include_inactive', '').lower() == 'true'

        if current_user.is_admin:
            # Admins can see all subjects
            subjects = Subject.get_all(include_inactive=include_inactive)
        elif current_user.is_teacher:
            # Teachers can see their subjects
            subjects = Subject.get_by_teacher(current_user.id)
        else:
            # Students can see active subjects
            subjects = Subject.get_all(include_inactive=False)

        return jsonify({
            'subjects': [subject.to_dict() for subject in subjects]
        }), 200

    except Exception as e:
        logger.error(f"Error listing subjects: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/<subject_id>', methods=['GET'])
@login_required
def get_subject(subject_id):
    """Get subject details"""
    try:
        subject = Subject.get_by_id(subject_id)
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404

        # Check access based on role
        if current_user.is_teacher and subject.teacher_id != current_user.id:
            return jsonify({'error': 'Unauthorized to view this subject'}), 403

        return jsonify(subject.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting subject: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/<subject_id>', methods=['PUT'])
@login_required
@teacher_required
def update_subject(subject_id):
    """Update subject details"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        subject = Subject.get_by_id(subject_id)
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404

        # Check if user is authorized to update
        if current_user.is_teacher and subject.teacher_id != current_user.id:
            return jsonify({'error': 'Unauthorized to update this subject'}), 403

        # Update fields
        if 'name' in data:
            subject.name = data['name']
        if 'description' in data:
            subject.description = data['description']
        if 'schedule' in data:
            subject.schedule = data['schedule']
        if 'is_active' in data and current_user.is_admin:
            subject.is_active = data['is_active']

        subject.save()

        return jsonify({
            'message': 'Subject updated successfully',
            'subject': subject.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error updating subject: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/<subject_id>', methods=['DELETE'])
@login_required
@teacher_required
def delete_subject(subject_id):
    """Delete subject"""
    try:
        subject = Subject.get_by_id(subject_id)
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404

        # Only admin or the assigned teacher can delete
        if current_user.is_teacher and subject.teacher_id != current_user.id:
            return jsonify({'error': 'Unauthorized to delete this subject'}), 403

        subject.delete()

        return jsonify({
            'message': 'Subject deleted successfully',
            'subject_id': subject_id
        }), 200

    except Exception as e:
        logger.error(f"Error deleting subject: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/<subject_id>/attendance', methods=['GET'])
@login_required
def get_subject_attendance(subject_id):
    """Get subject attendance statistics"""
    try:
        subject = Subject.get_by_id(subject_id)
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404

        # Check access based on role
        if current_user.is_teacher and subject.teacher_id != current_user.id:
            return jsonify({'error': 'Unauthorized to view this subject'}), 403

        # Get attendance stats
        stats = subject.get_attendance_stats()
        if not stats:
            return jsonify({'error': 'No attendance records found'}), 404

        # Get AI insights if requested
        if request.args.get('include_insights', '').lower() == 'true':
            ai_service = AIService(api_key=current_app.config['GEMINI_API_KEY'])
            insights = ai_service.generate_attendance_insights(stats)
            stats['insights'] = insights

        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"Error getting subject attendance: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/<subject_id>/schedule', methods=['PUT'])
@login_required
@teacher_required
def update_subject_schedule(subject_id):
    """Update subject schedule"""
    try:
        data = request.get_json()
        if not data or 'schedule' not in data:
            return jsonify({'error': 'No schedule provided'}), 400

        subject = Subject.get_by_id(subject_id)
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404

        # Check if user is authorized to update
        if current_user.is_teacher and subject.teacher_id != current_user.id:
            return jsonify({'error': 'Unauthorized to update this subject'}), 403

        # Update schedule
        if subject.update_schedule(data['schedule']):
            return jsonify({
                'message': 'Schedule updated successfully',
                'subject': subject.to_dict()
            }), 200
        else:
            return jsonify({'error': 'Failed to update schedule'}), 500

    except Exception as e:
        logger.error(f"Error updating subject schedule: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/<subject_id>/teacher', methods=['PUT'])
@login_required
@teacher_required
def assign_teacher(subject_id):
    """Assign teacher to subject (admin only)"""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Admin privileges required'}), 403

        data = request.get_json()
        if not data or 'teacher_id' not in data or 'teacher_name' not in data:
            return jsonify({'error': 'Missing teacher information'}), 400

        subject = Subject.get_by_id(subject_id)
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404

        # Assign teacher
        if subject.assign_teacher(data['teacher_id'], data['teacher_name']):
            return jsonify({
                'message': 'Teacher assigned successfully',
                'subject': subject.to_dict()
            }), 200
        else:
            return jsonify({'error': 'Failed to assign teacher'}), 500

    except Exception as e:
        logger.error(f"Error assigning teacher: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 