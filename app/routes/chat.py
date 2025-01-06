from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.services.ai_service import AIService
from app.services.db_service import DatabaseService

chat = Blueprint('chat', __name__)
ai = AIService()
db = DatabaseService()

@chat.route('/message', methods=['POST'])
@login_required
def message():
    """
    Handle chat messages and get AI responses.
    """
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({
            'success': False,
            'message': 'No message provided'
        })
    
    user_message = data['message'].strip()
    if not user_message:
        return jsonify({
            'success': False,
            'message': 'Message cannot be empty'
        })
    
    try:
        # Get user context
        context = {
            'user_id': current_user.id,
            'user_role': current_user.role,
            'user_name': current_user.first_name
        }
        
        if current_user.is_student():
            # Get student's attendance data
            attendance_records = db.get_student_attendance(current_user.id)
            attendance_percentage = db.get_student_attendance_percentage(current_user.id)
            subjects = db.get_student_subjects(current_user.class_name, current_user.division)
            
            context.update({
                'class_name': current_user.class_name,
                'division': current_user.division,
                'attendance_percentage': attendance_percentage,
                'attendance_records': attendance_records,
                'subjects': subjects
            })
            
        elif current_user.is_teacher():
            # Get teacher's subjects and attendance data
            subjects = db.get_teacher_subjects(current_user.id)
            attendance_stats = db.get_attendance_stats_by_teacher(current_user.id)
            
            context.update({
                'subjects': subjects,
                'attendance_stats': attendance_stats
            })
        
        # Get AI response
        response = ai.get_response(user_message, context)
        
        # Save chat history
        chat_message = {
            'user_id': current_user.id,
            'message': user_message,
            'response': response,
            'timestamp': db.get_current_timestamp()
        }
        db.save_chat_message(chat_message)
        
        return jsonify({
            'success': True,
            'message': response
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred while processing your message'
        })

@chat.route('/analyze', methods=['POST'])
@login_required
def analyze():
    """
    Analyze attendance patterns and provide insights.
    """
    try:
        if current_user.is_student():
            # Analyze student's attendance
            attendance_records = db.get_student_attendance(current_user.id)
            analysis = ai.analyze_attendance_pattern(attendance_records)
            
            return jsonify({
                'success': True,
                'analysis': analysis
            })
            
        elif current_user.is_teacher():
            subject_id = request.form.get('subject_id')
            if not subject_id:
                return jsonify({
                    'success': False,
                    'message': 'Subject ID is required'
                })
            
            # Verify teacher has access to subject
            subject = db.get_subject_by_id(subject_id)
            if not subject or subject['teacher_id'] != current_user.id:
                return jsonify({
                    'success': False,
                    'message': 'Access denied'
                })
            
            # Analyze subject attendance
            attendance_records = db.get_attendance_by_subject(subject_id)
            analysis = ai.analyze_subject_attendance(attendance_records)
            
            return jsonify({
                'success': True,
                'analysis': analysis
            })
            
        else:  # Admin
            subject_id = request.form.get('subject_id')
            class_name = request.form.get('class_name')
            division = request.form.get('division')
            
            if subject_id:
                # Analyze subject attendance
                attendance_records = db.get_attendance_by_subject(subject_id)
                analysis = ai.analyze_subject_attendance(attendance_records)
            elif class_name and division:
                # Analyze class attendance
                attendance_records = db.get_attendance_by_class(class_name, division)
                analysis = ai.analyze_class_attendance(attendance_records)
            else:
                # Analyze overall attendance
                attendance_records = db.get_all_attendance()
                analysis = ai.analyze_overall_attendance(attendance_records)
            
            return jsonify({
                'success': True,
                'analysis': analysis
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred while analyzing attendance'
        })

@chat.route('/suggest', methods=['POST'])
@login_required
def suggest():
    """
    Get AI suggestions for improving attendance.
    """
    try:
        if current_user.is_student():
            # Get personalized suggestions for student
            attendance_records = db.get_student_attendance(current_user.id)
            suggestions = ai.get_student_suggestions(attendance_records)
            
            return jsonify({
                'success': True,
                'suggestions': suggestions
            })
            
        elif current_user.is_teacher():
            subject_id = request.form.get('subject_id')
            if not subject_id:
                return jsonify({
                    'success': False,
                    'message': 'Subject ID is required'
                })
            
            # Verify teacher has access to subject
            subject = db.get_subject_by_id(subject_id)
            if not subject or subject['teacher_id'] != current_user.id:
                return jsonify({
                    'success': False,
                    'message': 'Access denied'
                })
            
            # Get suggestions for improving subject attendance
            attendance_records = db.get_attendance_by_subject(subject_id)
            suggestions = ai.get_subject_suggestions(attendance_records)
            
            return jsonify({
                'success': True,
                'suggestions': suggestions
            })
            
        else:  # Admin
            # Get system-wide suggestions
            attendance_records = db.get_all_attendance()
            suggestions = ai.get_system_suggestions(attendance_records)
            
            return jsonify({
                'success': True,
                'suggestions': suggestions
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred while getting suggestions'
        })

@chat.route('/history')
@login_required
def history():
    """
    Get user's chat history.
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        chat_history = db.get_chat_history(
            user_id=current_user.id,
            page=page,
            per_page=per_page
        )
        
        return jsonify({
            'success': True,
            'history': chat_history
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': 'An error occurred while fetching chat history'
        }) 