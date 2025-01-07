from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app.services.ai_service import GeminiAIService

bp = Blueprint('chat', __name__)

@bp.route('/chat', methods=['POST'])
@login_required
def chat():
    """Handle chat messages with AI assistant"""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided'}), 400

        message = data['message']
        ai_service = GeminiAIService()
        
        # Get user context
        context = {
            'user_role': current_user.role,
            'user_name': current_user.first_name
        }
        
        # Get AI response
        response = ai_service.get_response(message, context)
        
        return jsonify({'response': response})

    except Exception as e:
        current_app.logger.error(f"Error in chat route: {str(e)}")
        return jsonify({'error': 'An error occurred processing your message'}), 500 