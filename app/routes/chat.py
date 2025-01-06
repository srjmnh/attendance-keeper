from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user

from ..models.user import User
from ..models.subject import Subject
from ..models.attendance import Attendance
from .. import ai_service, db_service

bp = Blueprint('chat', __name__, url_prefix='/chat')

@bp.route('/message', methods=['POST'])
@login_required
def send_message():
    """Send message to AI chatbot"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400

        # Get context data if provided
        context = {
            'user_id': current_user.id,
            'user_role': current_user.role,
            'subject_id': data.get('subject_id'),
            'student_id': data.get('student_id'),
            'date_range': data.get('date_range')
        }

        # Get relevant data based on context
        if context['subject_id']:
            subject = Subject.get_by_id(context['subject_id'])
            if not subject:
                return jsonify({'error': 'Subject not found'}), 404
            
            # Check access permissions
            if current_user.is_student and subject.id not in current_user.classes:
                return jsonify({'error': 'Unauthorized'}), 403
            if current_user.is_teacher and subject.id not in current_user.classes:
                return jsonify({'error': 'Unauthorized'}), 403
            
            context['subject'] = subject.to_dict()

        if context['student_id']:
            student = User.get_by_id(context['student_id'])
            if not student or not student.is_student:
                return jsonify({'error': 'Student not found'}), 404
            
            # Teachers can only view their students
            if current_user.is_teacher:
                student_subjects = set(student.classes)
                teacher_subjects = set(current_user.classes)
                if not student_subjects.intersection(teacher_subjects):
                    return jsonify({'error': 'Unauthorized'}), 403
            
            context['student'] = student.to_dict()

        # Get attendance records if needed
        if context['subject_id'] or context['student_id']:
            records = db_service.get_attendance(
                student_id=context['student_id'],
                subject_id=context['subject_id'],
                start_date=context['date_range'].get('start') if context['date_range'] else None,
                end_date=context['date_range'].get('end') if context['date_range'] else None,
                teacher_classes=current_user.classes if current_user.is_teacher else None
            )
            context['attendance_records'] = [r.to_dict() for r in records]

        # Process message with AI
        response = ai_service.process_chat(
            message=data['message'],
            context=context,
            conversation_id=data.get('conversation_id')
        )

        return jsonify({
            'message': response.get('message'),
            'conversation_id': response.get('conversation_id'),
            'suggestions': response.get('suggestions'),
            'insights': response.get('insights')
        })

    except Exception as e:
        current_app.logger.error(f"Error processing chat message: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/analyze', methods=['POST'])
@login_required
def analyze_data():
    """Request AI analysis of specific data"""
    try:
        data = request.get_json()
        if not data or 'analysis_type' not in data:
            return jsonify({'error': 'Analysis type is required'}), 400

        analysis_type = data['analysis_type']
        subject_id = data.get('subject_id')
        student_id = data.get('student_id')
        date_range = data.get('date_range')

        # Validate access permissions
        if subject_id:
            subject = Subject.get_by_id(subject_id)
            if not subject:
                return jsonify({'error': 'Subject not found'}), 404
            
            if current_user.is_student and subject.id not in current_user.classes:
                return jsonify({'error': 'Unauthorized'}), 403
            if current_user.is_teacher and subject.id not in current_user.classes:
                return jsonify({'error': 'Unauthorized'}), 403

        if student_id:
            student = User.get_by_id(student_id)
            if not student or not student.is_student:
                return jsonify({'error': 'Student not found'}), 404
            
            if current_user.is_teacher:
                student_subjects = set(student.classes)
                teacher_subjects = set(current_user.classes)
                if not student_subjects.intersection(teacher_subjects):
                    return jsonify({'error': 'Unauthorized'}), 403

        # Get data for analysis
        if analysis_type == 'attendance':
            records = db_service.get_attendance(
                student_id=student_id,
                subject_id=subject_id,
                start_date=date_range.get('start') if date_range else None,
                end_date=date_range.get('end') if date_range else None,
                teacher_classes=current_user.classes if current_user.is_teacher else None
            )
            analysis = ai_service.analyze_attendance_patterns(
                [r.to_dict() for r in records]
            )
        
        elif analysis_type == 'subject':
            if not subject_id:
                return jsonify({'error': 'Subject ID is required'}), 400
            subject = Subject.get_by_id(subject_id)
            analysis = ai_service.analyze_subject_patterns(
                [subject.to_dict()]
            )
        
        elif analysis_type == 'schedule':
            if not subject_id:
                return jsonify({'error': 'Subject ID is required'}), 400
            subject = Subject.get_by_id(subject_id)
            schedule = subject.get_schedule()
            analysis = ai_service.analyze_schedule_patterns(schedule)
        
        elif analysis_type == 'student':
            if not student_id:
                return jsonify({'error': 'Student ID is required'}), 400
            student = User.get_by_id(student_id)
            analysis = ai_service.analyze_student_patterns(
                student.to_dict()
            )
        
        else:
            return jsonify({'error': 'Invalid analysis type'}), 400

        return jsonify({
            'analysis': analysis.get('analysis'),
            'recommendations': analysis.get('recommendations'),
            'insights': analysis.get('insights')
        })

    except Exception as e:
        current_app.logger.error(f"Error analyzing data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/suggest', methods=['POST'])
@login_required
def get_suggestions():
    """Get AI suggestions for various scenarios"""
    try:
        data = request.get_json()
        if not data or 'suggestion_type' not in data:
            return jsonify({'error': 'Suggestion type is required'}), 400

        suggestion_type = data['suggestion_type']
        context = {
            'user_id': current_user.id,
            'user_role': current_user.role,
            'subject_id': data.get('subject_id'),
            'student_id': data.get('student_id'),
            'date_range': data.get('date_range')
        }

        # Get suggestions based on type
        if suggestion_type == 'schedule_optimization':
            if not context['subject_id']:
                return jsonify({'error': 'Subject ID is required'}), 400
            
            subject = Subject.get_by_id(context['subject_id'])
            if not subject:
                return jsonify({'error': 'Subject not found'}), 404
            
            suggestions = ai_service.suggest_schedule_optimization(
                subject.to_dict(),
                context
            )
        
        elif suggestion_type == 'attendance_improvement':
            if not context['student_id']:
                return jsonify({'error': 'Student ID is required'}), 400
            
            student = User.get_by_id(context['student_id'])
            if not student:
                return jsonify({'error': 'Student not found'}), 404
            
            suggestions = ai_service.suggest_attendance_improvement(
                student.to_dict(),
                context
            )
        
        elif suggestion_type == 'teaching_strategies':
            if not context['subject_id']:
                return jsonify({'error': 'Subject ID is required'}), 400
            
            subject = Subject.get_by_id(context['subject_id'])
            if not subject:
                return jsonify({'error': 'Subject not found'}), 404
            
            suggestions = ai_service.suggest_teaching_strategies(
                subject.to_dict(),
                context
            )
        
        else:
            return jsonify({'error': 'Invalid suggestion type'}), 400

        return jsonify({
            'suggestions': suggestions.get('suggestions'),
            'rationale': suggestions.get('rationale'),
            'implementation_steps': suggestions.get('implementation_steps')
        })

    except Exception as e:
        current_app.logger.error(f"Error getting suggestions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/conversations', methods=['GET'])
@login_required
def get_conversations():
    """Get user's chat conversations"""
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))

        conversations = ai_service.get_conversations(
            user_id=current_user.id,
            page=page,
            per_page=per_page
        )

        return jsonify({
            'conversations': conversations.get('conversations', []),
            'total_conversations': conversations.get('total', 0),
            'page': page,
            'per_page': per_page,
            'total_pages': conversations.get('total_pages', 0)
        })

    except Exception as e:
        current_app.logger.error(f"Error getting conversations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/conversations/<conversation_id>', methods=['GET'])
@login_required
def get_conversation_history(conversation_id):
    """Get chat conversation history"""
    try:
        history = ai_service.get_conversation_history(
            conversation_id=conversation_id,
            user_id=current_user.id
        )

        if not history:
            return jsonify({'error': 'Conversation not found'}), 404

        return jsonify(history)

    except Exception as e:
        current_app.logger.error(f"Error getting conversation history: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/conversations/<conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation(conversation_id):
    """Delete chat conversation"""
    try:
        success = ai_service.delete_conversation(
            conversation_id=conversation_id,
            user_id=current_user.id
        )

        if not success:
            return jsonify({'error': 'Failed to delete conversation'}), 500

        return jsonify({'message': 'Conversation deleted successfully'})

    except Exception as e:
        current_app.logger.error(f"Error deleting conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500 