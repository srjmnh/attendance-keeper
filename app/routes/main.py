from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
from app.services.db_service import DatabaseService

main = Blueprint('main', __name__)

@main.route('/')
@login_required
def index():
    """Main dashboard route"""
    try:
        db = DatabaseService()
        error = None
        attendance_stats = None
        subjects = []

        # Get subjects based on user role
        if current_user.is_student():
            subjects = db.get_student_subjects(current_user.id)
            attendance_stats = db.get_student_attendance_percentage(current_user.id)
        elif current_user.is_teacher():
            subjects = db.get_teacher_subjects(current_user.id)
            attendance_stats = db.get_teacher_attendance_stats(current_user.id)
        else:  # Admin
            subjects = db.get_all_subjects()
            attendance_stats = db.get_system_attendance_stats()

        # Get recent activities
        recent_activities = []
        if current_user.is_student():
            recent_activities = db.get_recent_attendance_by_student(current_user.id)
        elif current_user.is_teacher():
            recent_activities = db.get_recent_attendance_by_teacher(current_user.id)
        else:
            recent_activities = db.get_recent_activities()

        return render_template('main/index.html',
                             subjects=subjects,
                             attendance_stats=attendance_stats,
                             recent_activities=recent_activities,
                             error=error)

    except Exception as e:
        current_app.logger.error(f"Error in main route: {str(e)}")
        error = "An error occurred while loading the dashboard. Please try again later."
        return render_template('main/index.html', error=error)

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