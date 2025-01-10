from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app.utils.decorators import role_required
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard view"""
    try:
        user = current_user
        subjects = []
        recent_activities = []

        # Get subjects based on user role
        if user.role == 'admin':
            subjects_ref = current_app.db.collection('subjects').stream()
            subjects = [{
                'id': doc.id,
                'name': doc.to_dict().get('name', '')
            } for doc in subjects_ref]
        elif user.role == 'teacher':
            if hasattr(user, 'classes'):
                subject_ids = user.classes
                subjects = []
                for subject_id in subject_ids:
                    doc = current_app.db.collection('subjects').document(subject_id).get()
                    if doc.exists:
                        subjects.append({
                            'id': doc.id,
                            'name': doc.to_dict().get('name', '')
                        })

        # Get recent activities (last 10 attendance records)
        if user.role in ['admin', 'teacher']:
            activities_query = current_app.db.collection('attendance')\
                .order_by('timestamp', direction='DESCENDING')\
                .limit(10)
            
            if user.role == 'teacher' and hasattr(user, 'classes'):
                activities_query = activities_query.where('subject_id', 'in', user.classes)
            
            activities = activities_query.get()
            recent_activities = [{
                'student_name': doc.to_dict().get('name', ''),
                'student_id': doc.to_dict().get('student_id', ''),
                'subject_name': doc.to_dict().get('subject_name', ''),
                'timestamp': doc.to_dict().get('timestamp', ''),
                'status': doc.to_dict().get('status', '')
            } for doc in activities]
        elif user.role == 'student':
            activities = current_app.db.collection('attendance')\
                .where('student_id', '==', user.student_id)\
                .order_by('timestamp', direction='DESCENDING')\
                .limit(10)\
                .get()
            recent_activities = [{
                'subject_name': doc.to_dict().get('subject_name', ''),
                'timestamp': doc.to_dict().get('timestamp', ''),
                'status': doc.to_dict().get('status', '')
            } for doc in activities]

        return render_template('dashboard/index.html', 
                             subjects=subjects,
                             recent_activities=recent_activities,
                             user_role=user.role)

    except Exception as e:
        current_app.logger.error(f"Error loading dashboard: {str(e)}")
        return render_template('dashboard/index.html', 
                             subjects=[],
                             recent_activities=[],
                             user_role=current_user.role) 