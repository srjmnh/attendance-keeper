from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.utils.decorators import student_required
from app.models.attendance import Attendance
from app.models.subject import Subject
from datetime import datetime

bp = Blueprint('student', __name__)

@bp.route('/student/dashboard')
@login_required
@student_required
def dashboard():
    """Student dashboard showing attendance overview"""
    # Get student's subjects
    subjects = Subject.query.filter_by(class_name=current_user.class_name, division=current_user.division).all()
    
    # Get recent attendance
    recent_attendance = Attendance.query.filter_by(student_id=current_user.id).order_by(Attendance.date.desc()).limit(5).all()
    
    # Calculate attendance percentage
    total_classes = Attendance.query.filter_by(student_id=current_user.id).count()
    present_classes = Attendance.query.filter_by(student_id=current_user.id, status='present').count()
    attendance_percentage = (present_classes / total_classes * 100) if total_classes > 0 else 0
    
    return render_template('student/dashboard.html',
                         subjects=subjects,
                         recent_attendance=recent_attendance,
                         attendance_percentage=attendance_percentage)

@bp.route('/student/view-attendance')
@login_required
@student_required
def view_attendance():
    """View attendance records for the student"""
    subject_id = request.args.get('subject_id')
    start_date = request.args.get('start_date', datetime.now().replace(day=1).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    # Get student's subjects
    subjects = Subject.query.filter_by(class_name=current_user.class_name, division=current_user.division).all()
    
    # Get attendance records
    query = Attendance.query.filter_by(student_id=current_user.id)
    
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        query = query.filter(Attendance.date.between(start, end))
    except ValueError:
        pass
    
    attendance_records = query.order_by(Attendance.date.desc()).all()
    
    return render_template('student/view_attendance.html',
                         subjects=subjects,
                         attendance_records=attendance_records,
                         selected_subject=subject_id,
                         start_date=start_date,
                         end_date=end_date) 