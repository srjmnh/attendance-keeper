from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from ..models.user import User
from ..models.subject import Subject
from ..models.attendance import Attendance
from ..services.ai_service import AIService
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('index', __name__)

@bp.route('/')
def index():
    """Redirect to login if not authenticated, otherwise show dashboard"""
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    return redirect(url_for('index.dashboard'))

@bp.route('/dashboard')
@login_required
def dashboard():
    """Show dashboard with relevant statistics and insights"""
    try:
        stats = {}
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        # Get today's attendance
        attendance_today = len(Attendance.get_by_subject(
            subject_id=None,
            start_date=today_start,
            end_date=today_end
        ))
        stats['attendance_today'] = attendance_today

        if current_user.is_admin:
            # Admin sees all stats
            stats['total_users'] = len(User.get_all())
            stats['total_subjects'] = len(Subject.get_all())
            stats['total_students'] = len([u for u in User.get_all() if u.is_student])

            # Get recent activity
            recent_activity = []
            week_ago = datetime.utcnow() - timedelta(days=7)
            subjects = {s.id: s.name for s in Subject.get_all()}
            
            for record in Attendance.get_by_subject(None, week_ago):
                recent_activity.append({
                    'timestamp': record.timestamp,
                    'student_name': record.name,
                    'subject_name': subjects.get(record.subject_id, 'Unknown Subject'),
                    'status': record.status
                })

            # Get AI insights
            ai_service = AIService(api_key=current_app.config['GEMINI_API_KEY'])
            insights = ai_service.generate_attendance_insights(recent_activity)

            return render_template('dashboard.html',
                                stats=stats,
                                recent_activity=sorted(recent_activity, 
                                                     key=lambda x: x['timestamp'],
                                                     reverse=True)[:10],
                                insights=insights.get('insights') if insights else None)

        elif current_user.is_teacher:
            # Teacher sees stats for their subjects
            teacher_subjects = Subject.get_by_teacher(current_user.id)
            stats['total_subjects'] = len(teacher_subjects)
            
            # Get students in teacher's subjects
            student_set = set()
            for subject in teacher_subjects:
                records = Attendance.get_by_subject(subject.id)
                student_set.update(r.student_id for r in records)
            stats['total_students'] = len(student_set)

            # Get recent activity for teacher's subjects
            recent_activity = []
            week_ago = datetime.utcnow() - timedelta(days=7)
            subject_ids = [s.id for s in teacher_subjects]
            
            for subject_id in subject_ids:
                records = Attendance.get_by_subject(subject_id, week_ago)
                for record in records:
                    recent_activity.append({
                        'timestamp': record.timestamp,
                        'student_name': record.name,
                        'subject_name': record.subject_name,
                        'status': record.status
                    })

            # Get AI insights
            ai_service = AIService(api_key=current_app.config['GEMINI_API_KEY'])
            insights = ai_service.generate_attendance_insights(recent_activity)

            return render_template('dashboard.html',
                                stats=stats,
                                recent_activity=sorted(recent_activity,
                                                     key=lambda x: x['timestamp'],
                                                     reverse=True)[:10],
                                insights=insights.get('insights') if insights else None)

        else:  # Student
            # Get student's attendance summary
            attendance_summary = []
            subjects = Subject.get_all()
            
            for subject in subjects:
                records = Attendance.get_by_student(
                    current_user.id,
                    subject_id=subject.id
                )
                
                present_count = len([r for r in records if r.status.upper() == 'PRESENT'])
                attendance_summary.append({
                    'name': subject.name,
                    'present_count': present_count,
                    'total_classes': len(records)
                })

            return render_template('dashboard.html',
                                stats=stats,
                                attendance_summary=attendance_summary)

    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        return render_template('dashboard.html',
                            stats={'error': 'Error loading statistics'},
                            error_message='An error occurred while loading the dashboard') 