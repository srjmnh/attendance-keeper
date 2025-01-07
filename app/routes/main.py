from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user

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
    
    # Get recent attendance records
    attendance_records = []
    attendance_ref = current_app.db.collection('attendance')
    
    if current_user.role == 'student':
        # Students see only their own attendance
        query = attendance_ref.where('student_id', '==', current_user.id).limit(10)
    else:
        # Teachers and admins see all attendance records
        query = attendance_ref.limit(10)
    
    for doc in query.stream():
        record = doc.to_dict()
        attendance_records.append({
            'timestamp': record.get('timestamp', ''),
            'name': record.get('name', ''),
            'subject_name': record.get('subject_name', '')
        })
    
    return render_template('dashboard.html',
                         subjects=subjects,
                         attendance_records=attendance_records) 