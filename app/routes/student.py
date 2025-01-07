from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.utils.decorators import student_required
from app.services.db_service import DatabaseService
from datetime import datetime

bp = Blueprint('student', __name__)

@bp.route('/student/dashboard')
@login_required
@student_required
def dashboard():
    """Student dashboard showing attendance overview"""
    db = DatabaseService()
    
    # Get student's subjects
    subjects = db.get_student_subjects(current_user.id)
    
    # Get recent attendance
    attendance_records = db.get_student_attendance(current_user.id)
    # Sort by date and limit to 5 most recent
    recent_attendance = sorted(attendance_records, key=lambda x: x.date, reverse=True)[:5]
    
    # Calculate attendance percentage
    attendance_percentage = db.get_student_attendance_percentage(current_user.id)
    
    return render_template('student/dashboard.html',
                         subjects=subjects,
                         recent_attendance=recent_attendance,
                         attendance_percentage=attendance_percentage)

@bp.route('/student/view-attendance')
@login_required
@student_required
def view_attendance():
    """View attendance records for the student"""
    db = DatabaseService()
    
    subject_id = request.args.get('subject_id')
    start_date = request.args.get('start_date', datetime.now().replace(day=1).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    # Get student's subjects
    subjects = db.get_student_subjects(current_user.id)
    
    # Get attendance records
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        attendance_records = db.get_student_attendance(
            current_user.id,
            subject_id=subject_id,
            start_date=start,
            end_date=end
        )
    except ValueError:
        attendance_records = []
    
    return render_template('student/view_attendance.html',
                         subjects=subjects,
                         attendance_records=attendance_records,
                         selected_subject=subject_id,
                         start_date=start_date,
                         end_date=end_date) 