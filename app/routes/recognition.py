"""Face recognition routes"""

import os
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from ..models.user import User
from ..models.subject import Subject
from ..models.attendance import Attendance
from .. import face_service, db_service, ai_service

bp = Blueprint('recognition', __name__, url_prefix='/recognition')

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['UPLOAD_EXTENSIONS']

@bp.route('/register', methods=['POST'])
@login_required
def register_face():
    """Register a face for a student"""
    try:
        # Check permissions
        if not current_user.is_admin and not current_user.is_teacher:
            return jsonify({'error': 'Unauthorized'}), 403

        # Validate request
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        image = request.files['image']
        if not image or not allowed_file(image.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        student_id = request.form.get('student_id')
        if not student_id:
            return jsonify({'error': 'Student ID is required'}), 400

        # Verify student exists and access permissions
        student = User.get_by_id(student_id)
        if not student or not student.is_student:
            return jsonify({'error': 'Invalid student ID'}), 404

        if current_user.is_teacher:
            student_subjects = set(student.classes)
            teacher_subjects = set(current_user.classes)
            if not student_subjects.intersection(teacher_subjects):
                return jsonify({'error': 'Unauthorized to register this student'}), 403

        # Save image temporarily
        filename = secure_filename(image.filename)
        temp_path = os.path.join(current_app.config['UPLOAD_PATH'], filename)
        image.save(temp_path)

        # Register face
        with open(temp_path, 'rb') as f:
            result = face_service.register_face(f.read(), student_id)

        # Clean up temporary file
        os.remove(temp_path)

        if 'error' in result:
            return jsonify({'error': result['error']}), 400

        # Update student record with face ID
        student.update({'face_id': result['face_id']})

        return jsonify({
            'message': 'Face registered successfully',
            'face_id': result['face_id'],
            'confidence': result['confidence'],
            'quality': result['quality']
        })

    except Exception as e:
        current_app.logger.error(f"Error registering face: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/recognize', methods=['POST'])
@login_required
def recognize_faces():
    """Recognize faces and mark attendance"""
    try:
        # Validate request
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        image = request.files['image']
        if not image or not allowed_file(image.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        subject_id = request.form.get('subject_id')
        if not subject_id:
            return jsonify({'error': 'Subject ID is required'}), 400

        # Verify subject and access permissions
        subject = Subject.get_by_id(subject_id)
        if not subject:
            return jsonify({'error': 'Invalid subject ID'}), 404

        if current_user.is_teacher and subject_id not in current_user.classes:
            return jsonify({'error': 'Unauthorized to mark attendance for this subject'}), 403

        # Save image temporarily
        filename = secure_filename(image.filename)
        temp_path = os.path.join(current_app.config['UPLOAD_PATH'], filename)
        image.save(temp_path)

        # Recognize faces
        with open(temp_path, 'rb') as f:
            matches = face_service.search_faces(f.read())

        # Clean up temporary file
        os.remove(temp_path)

        if not matches:
            return jsonify({'error': 'No faces recognized in the image'}), 400

        # Process matches and mark attendance
        attendance_records = []
        for match in matches:
            student_id = match['external_id']
            student = User.get_by_id(student_id)
            if not student:
                continue

            # Create attendance record
            attendance = Attendance.create(
                student_id=student_id,
                student_name=student.name,
                subject_id=subject_id,
                subject_name=subject.name,
                status='present',
                face_id=match['face_id'],
                confidence=match['confidence'],
                marked_by=current_user.id
            )

            if attendance:
                attendance_records.append(attendance.to_dict())

        # Get AI insights if requested
        insights = None
        if request.form.get('include_insights') == 'true':
            insights = ai_service.analyze_attendance_patterns(attendance_records)

        return jsonify({
            'message': f"Marked attendance for {len(attendance_records)} students",
            'records': attendance_records,
            'insights': insights.get('analysis') if insights else None
        })

    except Exception as e:
        current_app.logger.error(f"Error recognizing faces: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/verify', methods=['POST'])
@login_required
def verify_attendance():
    """Verify attendance record using face recognition"""
    try:
        # Validate request
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        image = request.files['image']
        if not image or not allowed_file(image.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        attendance_id = request.form.get('attendance_id')
        if not attendance_id:
            return jsonify({'error': 'Attendance ID is required'}), 400

        # Get attendance record
        attendance = Attendance.get_by_id(attendance_id)
        if not attendance:
            return jsonify({'error': 'Invalid attendance ID'}), 404

        # Check permissions
        if current_user.is_student and attendance.student_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        if current_user.is_teacher and attendance.subject_id not in current_user.classes:
            return jsonify({'error': 'Unauthorized'}), 403

        # Save image temporarily
        filename = secure_filename(image.filename)
        temp_path = os.path.join(current_app.config['UPLOAD_PATH'], filename)
        image.save(temp_path)

        # Verify face
        with open(temp_path, 'rb') as f:
            matches = face_service.search_faces(f.read())

        # Clean up temporary file
        os.remove(temp_path)

        if not matches:
            return jsonify({'error': 'No faces recognized in the image'}), 400

        # Check if any match corresponds to the attendance record
        verified = False
        confidence = 0
        for match in matches:
            if match['external_id'] == attendance.student_id:
                verified = True
                confidence = match['confidence']
                break

        # Update attendance record
        if verified:
            attendance.update({
                'verified': True,
                'verification_confidence': confidence,
                'verification_time': datetime.utcnow().isoformat(),
                'verified_by': current_user.id
            })

        return jsonify({
            'verified': verified,
            'confidence': confidence if verified else 0,
            'attendance': attendance.to_dict()
        })

    except Exception as e:
        current_app.logger.error(f"Error verifying attendance: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/stats', methods=['GET'])
@login_required
def get_recognition_stats():
    """Get face recognition statistics"""
    try:
        if not current_user.is_admin and not current_user.is_teacher:
            return jsonify({'error': 'Unauthorized'}), 403

        # Get date range
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Get statistics based on role
        if current_user.is_teacher:
            stats = db_service.get_face_recognition_stats(
                teacher_classes=current_user.classes,
                start_date=start_date,
                end_date=end_date
            )
        else:  # Admin
            stats = db_service.get_face_recognition_stats(
                start_date=start_date,
                end_date=end_date
            )

        # Get AI insights if requested
        if request.args.get('include_insights') == 'true':
            insights = ai_service.analyze_recognition_stats(stats)
            if insights:
                stats['insights'] = insights.get('analysis')
                stats['recommendations'] = insights.get('recommendations')

        return jsonify(stats)

    except Exception as e:
        current_app.logger.error(f"Error getting recognition stats: {str(e)}")
        return jsonify({'error': str(e)}), 500 