from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from app.utils.decorators import teacher_required
from app.services.face_service import FaceService
from app.services.image_service import ImageService
from app.services.db_service import DatabaseService
from datetime import datetime

bp = Blueprint('teacher', __name__)

@bp.route('/teacher/dashboard')
@login_required
@teacher_required
def dashboard():
    """Teacher dashboard showing overview of classes and recent attendance"""
    subjects = Subject.query.filter_by(teacher_id=current_user.id).all()
    recent_attendance = Attendance.query.filter_by(marked_by=current_user.id).order_by(Attendance.date.desc()).limit(5).all()
    return render_template('teacher/dashboard.html', subjects=subjects, recent_attendance=recent_attendance)

@bp.route('/teacher/mark-attendance', methods=['GET', 'POST'])
@login_required
@teacher_required
def mark_attendance():
    """Mark attendance using face recognition"""
    if request.method == 'POST':
        try:
            image_data = request.json.get('image')
            subject_id = request.json.get('subject_id')
            
            if not image_data or not subject_id:
                return jsonify({'error': 'Missing image or subject'}), 400
                
            # Process image and recognize faces
            image_service = ImageService()
            face_service = FaceService()
            
            image = image_service.process_base64_image(image_data)
            recognized_faces = face_service.recognize_faces(image)
            
            # Mark attendance for recognized students
            attendance_records = []
            for face in recognized_faces:
                attendance = Attendance(
                    student_id=face['student_id'],
                    subject_id=subject_id,
                    date=datetime.now(),
                    status='present',
                    marked_by=current_user.id
                )
                attendance_records.append(attendance)
            
            db.session.bulk_save_objects(attendance_records)
            db.session.commit()
            
            return jsonify({'message': f'Marked attendance for {len(attendance_records)} students'})
            
        except Exception as e:
            current_app.logger.error(f'Error marking attendance: {str(e)}')
            return jsonify({'error': 'Failed to mark attendance'}), 500
    
    subjects = Subject.query.filter_by(teacher_id=current_user.id).all()
    return render_template('teacher/take_attendance.html', subjects=subjects)

@bp.route('/teacher/view-subjects')
@login_required
@teacher_required
def view_subjects():
    """View subjects assigned to the teacher"""
    subjects = Subject.query.filter_by(teacher_id=current_user.id).all()
    return render_template('teacher/view_subjects.html', subjects=subjects)

@bp.route('/teacher/view-attendance/<int:subject_id>')
@login_required
@teacher_required
def view_attendance(subject_id):
    """View attendance records for a specific subject"""
    subject = Subject.query.get_or_404(subject_id)
    if subject.teacher_id != current_user.id:
        flash('You do not have permission to view this subject\'s attendance', 'error')
        return redirect(url_for('teacher.dashboard'))
        
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    attendance_records = Attendance.query.filter_by(subject_id=subject_id, date=date).all()
    return render_template('teacher/view_attendance.html', subject=subject, attendance_records=attendance_records, selected_date=date) 