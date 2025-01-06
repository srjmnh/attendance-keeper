from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from ..models.subject import Subject
from ..models.user import User
from .. import db_service, ai_service

bp = Blueprint('subject', __name__, url_prefix='/subject')

@bp.route('', methods=['GET'])
@login_required
def get_subjects():
    """Get subjects with optional filters"""
    try:
        # Parse query parameters
        teacher_id = request.args.get('teacher_id')
        student_id = request.args.get('student_id')
        active = request.args.get('active', 'true').lower() == 'true'
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 50))

        # Get subjects based on role and filters
        if current_user.is_student:
            subjects = Subject.get_by_student(current_user.id, active=active)
        elif current_user.is_teacher:
            subjects = Subject.get_by_teacher(current_user.id, active=active)
        else:  # Admin
            subjects = Subject.get_all(
                teacher_id=teacher_id,
                student_id=student_id,
                active=active
            )

        # Paginate results
        total_subjects = len(subjects)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_subjects = subjects[start_idx:end_idx]

        # Get AI insights if requested
        insights = None
        if request.args.get('include_insights') == 'true':
            insights = ai_service.analyze_subject_patterns(
                [s.to_dict() for s in subjects]
            )

        return jsonify({
            'subjects': [subject.to_dict() for subject in paginated_subjects],
            'total_subjects': total_subjects,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_subjects + per_page - 1) // per_page,
            'insights': insights.get('analysis') if insights else None
        })

    except Exception as e:
        current_app.logger.error(f"Error getting subjects: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<subject_id>', methods=['GET'])
@login_required
def get_subject(subject_id):
    """Get subject details"""
    try:
        subject = Subject.get_by_id(subject_id)
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404

        # Check access permissions
        if current_user.is_student:
            if subject_id not in current_user.classes:
                return jsonify({'error': 'Unauthorized'}), 403
        elif current_user.is_teacher:
            if subject_id not in current_user.classes:
                return jsonify({'error': 'Unauthorized'}), 403

        # Get AI insights if requested
        insights = None
        if request.args.get('include_insights') == 'true':
            insights = ai_service.analyze_subject_patterns(
                [subject.to_dict()]
            )

        response = subject.to_dict()
        if insights:
            response['insights'] = insights.get('analysis')

        return jsonify(response)

    except Exception as e:
        current_app.logger.error(f"Error getting subject: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('', methods=['POST'])
@login_required
def create_subject():
    """Create a new subject"""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        required_fields = ['name', 'code']
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            return jsonify({
                'error': f"Missing required fields: {', '.join(missing_fields)}"
            }), 400

        # Create subject
        subject = Subject.create(data)
        if not subject:
            return jsonify({'error': 'Subject code already exists'}), 400

        # Add teachers if provided
        if 'teachers' in data and isinstance(data['teachers'], list):
            for teacher_id in data['teachers']:
                teacher = User.get_by_id(teacher_id)
                if teacher and teacher.is_teacher:
                    subject.add_teacher(teacher_id)

        # Add students if provided
        if 'students' in data and isinstance(data['students'], list):
            for student_id in data['students']:
                student = User.get_by_id(student_id)
                if student and student.is_student:
                    subject.add_student(student_id)

        return jsonify({
            'message': 'Subject created successfully',
            'subject': subject.to_dict()
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error creating subject: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<subject_id>', methods=['PUT'])
@login_required
def update_subject(subject_id):
    """Update subject details"""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403

        subject = Subject.get_by_id(subject_id)
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Update basic details
        updates = {}
        if 'name' in data:
            updates['name'] = data['name']
        if 'code' in data:
            updates['code'] = data['code']
        if 'active' in data:
            updates['active'] = data['active']
        if 'description' in data:
            updates['description'] = data['description']
        if 'schedule' in data:
            updates['schedule'] = data['schedule']

        if updates:
            if not subject.update(updates):
                return jsonify({'error': 'Failed to update subject'}), 500

        # Update teachers if provided
        if 'teachers' in data and isinstance(data['teachers'], list):
            subject.set_teachers(data['teachers'])

        # Update students if provided
        if 'students' in data and isinstance(data['students'], list):
            subject.set_students(data['students'])

        return jsonify({
            'message': 'Subject updated successfully',
            'subject': subject.to_dict()
        })

    except Exception as e:
        current_app.logger.error(f"Error updating subject: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<subject_id>', methods=['DELETE'])
@login_required
def delete_subject(subject_id):
    """Delete a subject"""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403

        subject = Subject.get_by_id(subject_id)
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404

        # Delete subject
        if not subject.delete():
            return jsonify({'error': 'Failed to delete subject'}), 500

        return jsonify({'message': 'Subject deleted successfully'})

    except Exception as e:
        current_app.logger.error(f"Error deleting subject: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<subject_id>/students', methods=['GET'])
@login_required
def get_subject_students(subject_id):
    """Get students enrolled in a subject"""
    try:
        subject = Subject.get_by_id(subject_id)
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404

        # Check access permissions
        if current_user.is_teacher and subject_id not in current_user.classes:
            return jsonify({'error': 'Unauthorized'}), 403

        # Get students
        students = subject.get_students()

        return jsonify({
            'subject_id': subject_id,
            'subject_name': subject.name,
            'total_students': len(students),
            'students': [student.to_dict() for student in students]
        })

    except Exception as e:
        current_app.logger.error(f"Error getting subject students: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<subject_id>/teachers', methods=['GET'])
@login_required
def get_subject_teachers(subject_id):
    """Get teachers assigned to a subject"""
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403

        subject = Subject.get_by_id(subject_id)
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404

        # Get teachers
        teachers = subject.get_teachers()

        return jsonify({
            'subject_id': subject_id,
            'subject_name': subject.name,
            'total_teachers': len(teachers),
            'teachers': [teacher.to_dict() for teacher in teachers]
        })

    except Exception as e:
        current_app.logger.error(f"Error getting subject teachers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<subject_id>/schedule', methods=['GET'])
@login_required
def get_subject_schedule(subject_id):
    """Get subject schedule"""
    try:
        subject = Subject.get_by_id(subject_id)
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404

        # Check access permissions
        if current_user.is_student and subject_id not in current_user.classes:
            return jsonify({'error': 'Unauthorized'}), 403
        if current_user.is_teacher and subject_id not in current_user.classes:
            return jsonify({'error': 'Unauthorized'}), 403

        # Get schedule with AI insights
        schedule = subject.get_schedule()
        if request.args.get('include_insights') == 'true':
            insights = ai_service.analyze_schedule_patterns(schedule)
            if insights:
                schedule['insights'] = insights.get('analysis')

        return jsonify(schedule)

    except Exception as e:
        current_app.logger.error(f"Error getting subject schedule: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/<subject_id>/schedule', methods=['PUT'])
@login_required
def update_subject_schedule(subject_id):
    """Update subject schedule"""
    try:
        if not current_user.is_admin and not current_user.is_teacher:
            return jsonify({'error': 'Unauthorized'}), 403

        subject = Subject.get_by_id(subject_id)
        if not subject:
            return jsonify({'error': 'Subject not found'}), 404

        # Teachers can only update their subjects
        if current_user.is_teacher and subject_id not in current_user.classes:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        if not data or 'schedule' not in data:
            return jsonify({'error': 'No schedule data provided'}), 400

        # Update schedule
        if not subject.update_schedule(data['schedule']):
            return jsonify({'error': 'Failed to update schedule'}), 500

        return jsonify({
            'message': 'Schedule updated successfully',
            'schedule': subject.get_schedule()
        })

    except Exception as e:
        current_app.logger.error(f"Error updating subject schedule: {str(e)}")
        return jsonify({'error': str(e)}), 500 