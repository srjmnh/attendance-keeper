from flask import Blueprint, request, jsonify, current_app, render_template
from flask_login import login_required, current_user
from app.services.ai_service import GeminiAIService
from app.services.db_service import DatabaseService
from datetime import datetime

bp = Blueprint('chat', __name__)

@bp.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    """Handle chat messages with AI assistant"""
    if request.method == 'GET':
        return render_template('chat/chat.html')
        
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided'}), 400

        message = data['message']
        ai_service = GeminiAIService()
        db = DatabaseService()
        
        # Get user context
        context = {
            'user_id': current_user.id,
            'user_role': current_user.role,
            'user_name': current_user.first_name,
            'class_name': current_user.class_name if current_user.is_student() else None,
            'division': current_user.division if current_user.is_student() else None
        }
        
        # Add attendance context for students
        if current_user.is_student():
            attendance_stats = db.get_student_attendance_percentage(current_user.id)
            recent_attendance = db.get_recent_attendance_by_student(current_user.id, limit=5)
            context.update({
                'attendance_percentage': attendance_stats,
                'recent_attendance': recent_attendance
            })
        
        # Add teaching context for teachers
        elif current_user.is_teacher():
            teaching_stats = db.get_teacher_attendance_stats(current_user.id)
            subjects = db.get_teacher_subjects(current_user.id)
            context.update({
                'teaching_stats': teaching_stats,
                'subjects': [s.to_dict() for s in subjects]
            })
        
        # Add system context for admins
        elif current_user.is_admin():
            system_stats = db.get_system_attendance_stats()
            context.update({
                'system_stats': system_stats
            })
        
        # Get AI response
        response = ai_service.get_response(message, context)
        
        # Log chat interaction
        chat_log = {
            'user_id': current_user.id,
            'message': message,
            'response': response,
            'timestamp': datetime.utcnow().isoformat(),
            'context': context
        }
        db.log_chat_interaction(chat_log)
        
        return jsonify({
            'response': response,
            'context': {
                'role': current_user.role,
                'name': current_user.first_name
            }
        })

    except Exception as e:
        current_app.logger.error(f"Error in chat route: {str(e)}")
        return jsonify({'error': 'An error occurred processing your message'}), 500

@bp.route('/chat/history')
@login_required
def chat_history():
    """Get chat history for current user"""
    try:
        db = DatabaseService()
        history = db.get_chat_history(current_user.id)
        return jsonify({'history': history})
    except Exception as e:
        current_app.logger.error(f"Error getting chat history: {str(e)}")
        return jsonify({'error': 'An error occurred retrieving chat history'}), 500

@bp.route('/chat/analytics')
@login_required
def chat_analytics():
    """Get chat analytics"""
    try:
        if not current_user.is_admin():
            return jsonify({'error': 'Unauthorized'}), 403
            
        db = DatabaseService()
        analytics = db.get_chat_analytics()
        return jsonify(analytics)
    except Exception as e:
        current_app.logger.error(f"Error getting chat analytics: {str(e)}")
        return jsonify({'error': 'An error occurred retrieving chat analytics'}), 500 