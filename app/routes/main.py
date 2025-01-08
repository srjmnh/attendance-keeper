from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard view"""
    # Get subjects for teachers and admins
    subjects = []
    if current_user.role in ['admin', 'teacher']:
        subjects_ref = current_app.db.collection('subjects').stream()
        subjects = [{
            'id': doc.id,
            'name': doc.to_dict().get('name', '')
        } for doc in subjects_ref]
    
    # Get total students
    students_ref = current_app.db.collection('users').where('role', '==', 'student').stream()
    total_students = len(list(students_ref))
    
    # Get total subjects
    total_subjects = len(subjects)
    
    # Calculate today's attendance
    today = datetime.now().date()
    attendance_ref = current_app.db.collection('attendance')
    
    # Get today's attendance records
    today_query = attendance_ref.where('timestamp', '>=', today.isoformat())
    today_records = list(today_query.stream())
    
    # Calculate attendance percentage
    if today_records:
        present_count = len([r for r in today_records if r.to_dict().get('status') == 'PRESENT'])
        today_attendance = round((present_count / len(today_records)) * 100)
        
        # Calculate trend
        yesterday = today - timedelta(days=1)
        yesterday_query = attendance_ref.where('timestamp', '>=', yesterday.isoformat()).where('timestamp', '<', today.isoformat())
        yesterday_records = list(yesterday_query.stream())
        
        if yesterday_records:
            yesterday_present = len([r for r in yesterday_records if r.to_dict().get('status') == 'PRESENT'])
            yesterday_percentage = (yesterday_present / len(yesterday_records)) * 100
            trend_diff = today_attendance - yesterday_percentage
            attendance_trend = f"{'↑' if trend_diff > 0 else '↓'} {abs(round(trend_diff))}% vs yesterday"
        else:
            attendance_trend = "No data for yesterday"
    else:
        today_attendance = 0
        attendance_trend = "No attendance recorded today"
    
    # Get recent attendance records
    attendance_records = []
    query = attendance_ref
    
    if current_user.role == 'student':
        # Students see only their own attendance
        query = query.where('student_id', '==', current_user.id)
    elif current_user.role == 'teacher':
        # Teachers see attendance for their subjects
        query = query.where('subject_id', 'in', current_user.classes)
    
    query = query.order_by('timestamp', direction='DESCENDING').limit(10)
    
    for doc in query.stream():
        record = doc.to_dict()
        attendance_records.append({
            'timestamp': record.get('timestamp', ''),
            'name': record.get('name', ''),
            'subject_name': record.get('subject_name', ''),
            'status': record.get('status', '')
        })
    
    return render_template('dashboard.html',
                         total_students=total_students,
                         total_subjects=total_subjects,
                         today_attendance=today_attendance,
                         attendance_trend=attendance_trend,
                         attendance_records=attendance_records) 