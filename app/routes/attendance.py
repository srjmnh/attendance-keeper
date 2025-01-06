from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.services.db_service import DatabaseService
from app.services.face_service import FaceService
from app.services.image_service import ImageService
import base64
from datetime import datetime
import os

attendance = Blueprint('attendance', __name__)
db = DatabaseService()
face_service = FaceService()

# Set up upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
image_service = ImageService(UPLOAD_FOLDER)

@attendance.route('/mark', methods=['GET', 'POST'])
@login_required
def mark():
    """
    Mark attendance using face recognition.
    """
    if not current_user.is_teacher():
        flash('Access denied. Teachers only.', 'danger')
        return redirect(url_for('main.index'))
    
    teacher_subjects = db.get_teacher_subjects(current_user.id)
    
    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        image_data = request.form.get('image')
        
        if not subject_id or not image_data:
            return jsonify({'success': False, 'message': 'Missing required data'})
        
        try:
            # Save captured image
            image_data = base64.b64decode(image_data.split(',')[1])
            image_path = image_service.save_image(image_data)
            
            # Detect faces in image
            faces = face_service.detect_faces(image_path)
            if not faces:
                return jsonify({'success': False, 'message': 'No faces detected in image'})
            
            # Get subject details
            subject = db.get_subject_by_id(subject_id)
            if not subject:
                return jsonify({'success': False, 'message': 'Invalid subject'})
            
            # Get students for the class
            students = db.get_students_by_class(subject['class_name'], subject['division'])
            
            # Process each detected face
            attendance_records = []
            for face in faces:
                # Search for matching face
                match = face_service.search_face(face)
                if match:
                    student_id = match['student_id']
                    confidence = match['confidence']
                    
                    # Verify student belongs to class
                    if any(s['id'] == student_id for s in students):
                        # Record attendance
                        attendance = {
                            'student_id': student_id,
                            'subject_id': subject_id,
                            'date': datetime.now().isoformat(),
                            'status': 'present',
                            'confidence': confidence,
                            'image_url': image_path,
                            'marked_by': current_user.id
                        }
                        db.create_attendance(attendance)
                        attendance_records.append(attendance)
            
            # Clean up temporary image
            image_service.delete_image(image_path)
            
            return jsonify({
                'success': True,
                'message': f'Marked attendance for {len(attendance_records)} students',
                'records': attendance_records
            })
            
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)})
    
    return render_template('attendance/mark.html', subjects=teacher_subjects)

@attendance.route('/manage')
@login_required
def manage():
    """
    View and manage attendance records.
    """
    if current_user.is_student():
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))
    
    subjects = []
    if current_user.is_teacher():
        subjects = db.get_teacher_subjects(current_user.id)
    elif current_user.is_admin():
        subjects = db.get_all_subjects()
    
    return render_template('attendance/manage.html', subjects=subjects)

@attendance.route('/view')
@login_required
def view():
    """
    View attendance records.
    """
    if current_user.is_student():
        attendance_records = db.get_student_attendance(current_user.id)
        attendance_percentage = db.get_student_attendance_percentage(current_user.id)
        return render_template('attendance/view.html',
                             records=attendance_records,
                             percentage=attendance_percentage)
    
    subject_id = request.args.get('subject_id')
    date = request.args.get('date')
    
    if not subject_id:
        flash('Please select a subject.', 'warning')
        return redirect(url_for('attendance.manage'))
    
    subject = db.get_subject_by_id(subject_id)
    if not subject:
        flash('Invalid subject.', 'danger')
        return redirect(url_for('attendance.manage'))
    
    # Verify teacher has access to subject
    if current_user.is_teacher() and subject['teacher_id'] != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('attendance.manage'))
    
    attendance_records = db.get_attendance_by_subject(subject_id, date)
    return render_template('attendance/view.html',
                         subject=subject,
                         records=attendance_records,
                         selected_date=date)

@attendance.route('/edit', methods=['POST'])
@login_required
def edit():
    """
    Edit attendance record.
    """
    if current_user.is_student():
        return jsonify({'success': False, 'message': 'Access denied'})
    
    data = request.get_json()
    record_id = data.get('id')
    status = data.get('status')
    
    if not record_id or not status:
        return jsonify({'success': False, 'message': 'Missing required data'})
    
    try:
        record = db.get_attendance_by_id(record_id)
        if not record:
            return jsonify({'success': False, 'message': 'Invalid attendance record'})
        
        # Verify teacher has access to subject
        subject = db.get_subject_by_id(record['subject_id'])
        if current_user.is_teacher() and subject['teacher_id'] != current_user.id:
            return jsonify({'success': False, 'message': 'Access denied'})
        
        # Update attendance status
        db.update_attendance(record_id, {
            'status': status,
            'marked_by': current_user.id
        })
        
        return jsonify({'success': True, 'message': 'Attendance updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@attendance.route('/reports')
@login_required
def reports():
    """
    Generate attendance reports.
    """
    if current_user.is_student():
        flash('Access denied.', 'danger')
        return redirect(url_for('main.index'))
    
    subjects = []
    if current_user.is_teacher():
        subjects = db.get_teacher_subjects(current_user.id)
    elif current_user.is_admin():
        subjects = db.get_all_subjects()
    
    subject_id = request.args.get('subject_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    report_data = None
    if subject_id and start_date and end_date:
        subject = db.get_subject_by_id(subject_id)
        if not subject:
            flash('Invalid subject.', 'danger')
        elif current_user.is_teacher() and subject['teacher_id'] != current_user.id:
            flash('Access denied.', 'danger')
        else:
            report_data = db.generate_attendance_report(subject_id, start_date, end_date)
    
    return render_template('attendance/reports.html',
                         subjects=subjects,
                         report_data=report_data,
                         selected_subject=subject_id,
                         start_date=start_date,
                         end_date=end_date)

@attendance.route('/stats')
@login_required
def stats():
    """
    Get attendance statistics.
    """
    if current_user.is_student():
        percentage = db.get_student_attendance_percentage(current_user.id)
        return jsonify({'success': True, 'percentage': percentage})
    
    subject_id = request.args.get('subject_id')
    if not subject_id:
        return jsonify({'success': False, 'message': 'Subject ID required'})
    
    subject = db.get_subject_by_id(subject_id)
    if not subject:
        return jsonify({'success': False, 'message': 'Invalid subject'})
    
    if current_user.is_teacher() and subject['teacher_id'] != current_user.id:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    stats = db.get_attendance_stats_by_subject(subject_id)
    return jsonify({'success': True, 'stats': stats}) 