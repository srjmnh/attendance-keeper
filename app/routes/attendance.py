from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from ..models.attendance import Attendance
from ..services.ai_service import AIService
from datetime import datetime
from functools import wraps
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('attendance', __name__)

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

@bp.route('/records', methods=['GET'])
@login_required
def get_attendance_records():
    """Get attendance records with optional filters"""
    try:
        # Parse filters
        student_id = request.args.get('student_id')
        subject_id = request.args.get('subject_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Convert date strings to datetime objects
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # Get records based on user role
        if current_user.is_student:
            # Students can only view their own attendance
            records = Attendance.get_by_student(
                current_user.id,
                start_date=start_date,
                end_date=end_date,
                subject_id=subject_id
            )
        elif current_user.is_teacher:
            # Teachers can view attendance for their subjects
            if subject_id and subject_id not in current_user.subjects:
                return jsonify({'error': 'Unauthorized to view this subject'}), 403
            if student_id:
                records = Attendance.get_by_student(
                    student_id,
                    start_date=start_date,
                    end_date=end_date,
                    subject_id=subject_id
                )
            else:
                records = Attendance.get_by_subject(
                    subject_id,
                    start_date=start_date,
                    end_date=end_date
                )
        else:  # Admin
            if student_id:
                records = Attendance.get_by_student(
                    student_id,
                    start_date=start_date,
                    end_date=end_date,
                    subject_id=subject_id
                )
            elif subject_id:
                records = Attendance.get_by_subject(
                    subject_id,
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                return jsonify({'error': 'Please provide student_id or subject_id'}), 400

        # Convert records to dict for JSON response
        records_dict = [record.to_dict() for record in records]

        # Get AI insights if requested
        if request.args.get('include_insights') and records:
            ai_service = AIService(api_key=current_app.config['GEMINI_API_KEY'])
            insights = ai_service.generate_attendance_insights(records)
            return jsonify({
                'records': records_dict,
                'insights': insights
            }), 200

        return jsonify({'records': records_dict}), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting attendance records: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/records/<record_id>', methods=['PUT'])
@login_required
@teacher_required
def update_attendance(record_id):
    """Update an attendance record"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        record = Attendance.get_by_id(record_id)
        if not record:
            return jsonify({'error': 'Record not found'}), 404

        # Teachers can only update their subject's attendance
        if current_user.is_teacher and record.subject_id not in current_user.subjects:
            return jsonify({'error': 'Unauthorized to update this record'}), 403

        # Update allowed fields
        if 'status' in data:
            record.update_status(data['status'], verified_by=current_user.id)

        return jsonify({
            'message': 'Attendance record updated successfully',
            'record': record.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error updating attendance record: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/records/<record_id>/verify', methods=['POST'])
@login_required
@teacher_required
def verify_attendance(record_id):
    """Verify an attendance record"""
    try:
        record = Attendance.get_by_id(record_id)
        if not record:
            return jsonify({'error': 'Record not found'}), 404

        # Teachers can only verify their subject's attendance
        if current_user.is_teacher and record.subject_id not in current_user.subjects:
            return jsonify({'error': 'Unauthorized to verify this record'}), 403

        record.verify(verified_by=current_user.id)

        return jsonify({
            'message': 'Attendance record verified successfully',
            'record': record.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error verifying attendance record: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/insights', methods=['GET'])
@login_required
@teacher_required
def get_attendance_insights():
    """Get AI-powered insights for attendance patterns"""
    try:
        subject_id = request.args.get('subject_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not subject_id:
            return jsonify({'error': 'Subject ID is required'}), 400

        # Teachers can only view insights for their subjects
        if current_user.is_teacher and subject_id not in current_user.subjects:
            return jsonify({'error': 'Unauthorized to view this subject'}), 403

        # Convert date strings to datetime objects
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # Get attendance records
        records = Attendance.get_by_subject(subject_id, start_date, end_date)
        if not records:
            return jsonify({'error': 'No attendance records found'}), 404

        # Generate insights
        ai_service = AIService(api_key=current_app.config['GEMINI_API_KEY'])
        insights = ai_service.generate_attendance_insights(records)

        return jsonify(insights), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error getting attendance insights: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 