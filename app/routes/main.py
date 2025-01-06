from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.services.db_service import DatabaseService

main = Blueprint('main', __name__)
db = DatabaseService()

@main.route('/')
@login_required
def index():
    """
    Main dashboard route that displays different content based on user role.
    """
    if current_user.is_admin():
        # Get statistics for admin dashboard
        total_users = db.get_total_users()
        total_students = db.get_total_students()
        total_teachers = db.get_total_teachers()
        total_subjects = db.get_total_subjects()
        recent_activities = db.get_recent_activities(limit=5)
        
        return render_template('admin/dashboard.html',
                             total_users=total_users,
                             total_students=total_students,
                             total_teachers=total_teachers,
                             total_subjects=total_subjects,
                             recent_activities=recent_activities)
    
    elif current_user.is_teacher():
        # Get statistics for teacher dashboard
        teacher_subjects = db.get_teacher_subjects(current_user.id)
        recent_attendance = db.get_recent_attendance_by_teacher(current_user.id, limit=5)
        attendance_stats = db.get_attendance_stats_by_teacher(current_user.id)
        
        return render_template('teacher/dashboard.html',
                             subjects=teacher_subjects,
                             recent_attendance=recent_attendance,
                             attendance_stats=attendance_stats)
    
    else:  # Student
        # Get statistics for student dashboard
        student_subjects = db.get_student_subjects(current_user.class_name, current_user.division)
        attendance_records = db.get_student_attendance(current_user.id)
        attendance_percentage = db.get_student_attendance_percentage(current_user.id)
        recent_attendance = db.get_recent_attendance_by_student(current_user.id, limit=5)
        
        return render_template('student/dashboard.html',
                             subjects=student_subjects,
                             attendance_records=attendance_records,
                             attendance_percentage=attendance_percentage,
                             recent_attendance=recent_attendance)

@main.route('/profile')
@login_required
def profile():
    """
    User profile page.
    """
    if current_user.is_student():
        attendance_stats = db.get_student_attendance_percentage(current_user.id)
        recent_activities = db.get_recent_attendance_by_student(current_user.id, limit=5)
    else:
        attendance_stats = None
        recent_activities = None
    
    return render_template('auth/profile.html',
                         attendance_stats=attendance_stats,
                         recent_activities=recent_activities) 