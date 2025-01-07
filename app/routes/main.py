from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
from app.services.db_service import DatabaseService
import logging

main = Blueprint('main', __name__)
db = DatabaseService()
logger = logging.getLogger(__name__)

@main.route('/')
@login_required
def index():
    """
    Render the dashboard page.
    """
    try:
        error = None
        attendance_stats = None
        subjects = []
        
        if current_user.is_teacher():
            try:
                subjects = db.get_teacher_subjects(current_user.id)
            except Exception as e:
                logger.error(f"Error getting teacher subjects: {str(e)}")
                subjects = []
        
        elif current_user.is_student():
            try:
                subjects = db.get_student_subjects(current_user.id)
                attendance_stats = db.get_student_attendance_percentage(current_user.id)
            except Exception as e:
                logger.error(f"Error getting student data: {str(e)}")
                subjects = []
                attendance_stats = 0
        
        elif current_user.is_admin():
            try:
                attendance_stats = db.get_system_attendance_stats()
            except Exception as e:
                logger.error(f"Error getting system stats: {str(e)}")
                attendance_stats = None
        
        return render_template('main/index.html',
                             subjects=subjects,
                             attendance_stats=attendance_stats,
                             error=error)
                             
    except Exception as e:
        logger.error(f"Error in main route: {str(e)}")
        return render_template('main/index.html', error=str(e))

@main.route('/profile')
@login_required
def profile():
    """
    User profile page.
    """
    try:
        if current_user.is_student():
            attendance_stats = db.get_student_attendance_percentage(current_user.id)
            recent_activities = db.get_recent_attendance_by_student(current_user.id, limit=5)
        else:
            attendance_stats = None
            recent_activities = None
        
        return render_template('auth/profile.html',
                            attendance_stats=attendance_stats,
                            recent_activities=recent_activities)
    except Exception as e:
        logger.error(f"Error in profile route: {str(e)}")
        return render_template('auth/profile.html', error=str(e)) 