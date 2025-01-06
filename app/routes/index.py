from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from ..models.user import User
from ..models.subject import Subject
from ..models.attendance import Attendance
from .. import ai_service, db_service

bp = Blueprint('index', __name__)

@bp.route('/')
def home():
    """Home page route"""
    try:
        # Return basic application info
        return jsonify({
            'name': 'Facial Recognition Attendance System',
            'version': current_app.config.get('VERSION', '1.0.0'),
            'description': 'An intelligent attendance management system using facial recognition',
            'features': [
                'Facial recognition for attendance',
                'Real-time attendance tracking',
                'AI-powered insights and analytics',
                'Role-based access control',
                'Excel report generation',
                'Smart scheduling suggestions'
            ]
        })

    except Exception as e:
        current_app.logger.error(f"Error loading home page: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard route"""
    try:
        # Get user's role-specific dashboard data
        if current_user.is_student:
            # Get student's subjects
            subjects = Subject.get_by_student(current_user.id, active=True)
            
            # Get recent attendance records
            attendance = db_service.get_attendance(
                student_id=current_user.id,
                limit=5,
                order_by='timestamp',
                order='desc'
            )
            
            # Get AI insights
            insights = ai_service.analyze_student_patterns(
                current_user.to_dict()
            )
            
            return jsonify({
                'user': current_user.to_dict(),
                'subjects': [s.to_dict() for s in subjects],
                'recent_attendance': [a.to_dict() for a in attendance],
                'insights': insights.get('analysis') if insights else None,
                'recommendations': insights.get('recommendations') if insights else None
            })

        elif current_user.is_teacher:
            # Get teacher's subjects
            subjects = Subject.get_by_teacher(current_user.id, active=True)
            
            # Get recent attendance records for teacher's subjects
            attendance = db_service.get_attendance(
                teacher_classes=current_user.classes,
                limit=5,
                order_by='timestamp',
                order='desc'
            )
            
            # Get subject insights
            subject_insights = []
            for subject in subjects:
                insight = ai_service.analyze_subject_patterns(
                    [subject.to_dict()]
                )
                if insight:
                    subject_insights.append({
                        'subject_id': subject.id,
                        'subject_name': subject.name,
                        'analysis': insight.get('analysis'),
                        'recommendations': insight.get('recommendations')
                    })
            
            return jsonify({
                'user': current_user.to_dict(),
                'subjects': [s.to_dict() for s in subjects],
                'recent_attendance': [a.to_dict() for a in attendance],
                'subject_insights': subject_insights
            })

        else:  # Admin
            # Get system statistics
            stats = {
                'total_users': db_service.count_users(),
                'total_subjects': db_service.count_subjects(),
                'total_attendance': db_service.count_attendance(),
                'active_users': db_service.count_users(active=True),
                'active_subjects': db_service.count_subjects(active=True)
            }
            
            # Get recent activity
            recent_attendance = db_service.get_attendance(
                limit=5,
                order_by='timestamp',
                order='desc'
            )
            
            recent_users = User.get_recent(limit=5)
            recent_subjects = Subject.get_recent(limit=5)
            
            # Get system insights
            insights = ai_service.analyze_system_patterns()
            
            return jsonify({
                'user': current_user.to_dict(),
                'stats': stats,
                'recent_attendance': [a.to_dict() for a in recent_attendance],
                'recent_users': [u.to_dict() for u in recent_users],
                'recent_subjects': [s.to_dict() for s in recent_subjects],
                'insights': insights.get('analysis') if insights else None,
                'recommendations': insights.get('recommendations') if insights else None
            })

    except Exception as e:
        current_app.logger.error(f"Error loading dashboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/stats')
@login_required
def get_stats():
    """Get system statistics"""
    try:
        if not current_user.is_admin and not current_user.is_teacher:
            return jsonify({'error': 'Unauthorized'}), 403

        # Get date range
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Get statistics based on role
        if current_user.is_teacher:
            stats = {
                'total_students': db_service.count_users(
                    role='student',
                    teacher_classes=current_user.classes
                ),
                'total_subjects': db_service.count_subjects(
                    teacher_id=current_user.id
                ),
                'total_attendance': db_service.count_attendance(
                    teacher_classes=current_user.classes,
                    start_date=start_date,
                    end_date=end_date
                ),
                'attendance_by_status': db_service.get_attendance_by_status(
                    teacher_classes=current_user.classes,
                    start_date=start_date,
                    end_date=end_date
                ),
                'attendance_by_subject': db_service.get_attendance_by_subject(
                    teacher_classes=current_user.classes,
                    start_date=start_date,
                    end_date=end_date
                ),
                'face_recognition_stats': db_service.get_face_recognition_stats(
                    teacher_classes=current_user.classes,
                    start_date=start_date,
                    end_date=end_date
                )
            }
        else:  # Admin
            stats = {
                'total_users': db_service.count_users(),
                'total_subjects': db_service.count_subjects(),
                'total_attendance': db_service.count_attendance(
                    start_date=start_date,
                    end_date=end_date
                ),
                'users_by_role': db_service.get_users_by_role(),
                'attendance_by_status': db_service.get_attendance_by_status(
                    start_date=start_date,
                    end_date=end_date
                ),
                'attendance_by_subject': db_service.get_attendance_by_subject(
                    start_date=start_date,
                    end_date=end_date
                ),
                'face_recognition_stats': db_service.get_face_recognition_stats(
                    start_date=start_date,
                    end_date=end_date
                ),
                'system_usage': db_service.get_system_usage_stats(
                    start_date=start_date,
                    end_date=end_date
                )
            }

        # Get AI insights if requested
        if request.args.get('include_insights') == 'true':
            insights = ai_service.analyze_statistics(stats)
            if insights:
                stats['insights'] = insights.get('analysis')
                stats['recommendations'] = insights.get('recommendations')

        return jsonify(stats)

    except Exception as e:
        current_app.logger.error(f"Error getting statistics: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/search')
@login_required
def search():
    """Search across users, subjects, and attendance records"""
    try:
        # Get search parameters
        query = request.args.get('q')
        if not query:
            return jsonify({'error': 'Search query is required'}), 400

        search_type = request.args.get('type', 'all')  # all, users, subjects, attendance
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        results = {
            'query': query,
            'type': search_type,
            'page': page,
            'per_page': per_page
        }

        # Perform search based on type
        if search_type in ['all', 'users']:
            if current_user.is_teacher:
                users = db_service.search_users(
                    query,
                    role='student',
                    teacher_classes=current_user.classes,
                    page=page,
                    per_page=per_page
                )
            else:  # Admin
                users = db_service.search_users(
                    query,
                    page=page,
                    per_page=per_page
                )
            
            if search_type == 'users':
                results.update(users)
            else:
                results['users'] = users

        if search_type in ['all', 'subjects']:
            if current_user.is_student:
                subjects = Subject.search(
                    query,
                    student_id=current_user.id,
                    page=page,
                    per_page=per_page
                )
            elif current_user.is_teacher:
                subjects = Subject.search(
                    query,
                    teacher_id=current_user.id,
                    page=page,
                    per_page=per_page
                )
            else:  # Admin
                subjects = Subject.search(
                    query,
                    page=page,
                    per_page=per_page
                )
            
            if search_type == 'subjects':
                results.update(subjects)
            else:
                results['subjects'] = subjects

        if search_type in ['all', 'attendance']:
            if current_user.is_student:
                attendance = db_service.search_attendance(
                    query,
                    student_id=current_user.id,
                    page=page,
                    per_page=per_page
                )
            elif current_user.is_teacher:
                attendance = db_service.search_attendance(
                    query,
                    teacher_classes=current_user.classes,
                    page=page,
                    per_page=per_page
                )
            else:  # Admin
                attendance = db_service.search_attendance(
                    query,
                    page=page,
                    per_page=per_page
                )
            
            if search_type == 'attendance':
                results.update(attendance)
            else:
                results['attendance'] = attendance

        return jsonify(results)

    except Exception as e:
        current_app.logger.error(f"Error searching: {str(e)}")
        return jsonify({'error': str(e)}), 500 