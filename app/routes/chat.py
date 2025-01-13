from flask import Blueprint, jsonify, request, current_app, render_template
from flask_login import login_required
from app.services.chatbot_service import ChatbotService
import asyncio

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')
chatbot_service = ChatbotService()

# Initialize conversation memory
MAX_MEMORY = 20
conversation_memory = []

@chat_bp.route('/')
@login_required
def chat_page():
    """Render chat interface"""
    return render_template('chat/index.html')

@chat_bp.route('/ai/chat', methods=['POST'])
@login_required
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('prompt', '').strip()
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
            
        # Add user message to memory
        conversation_memory.append({"role": "user", "content": user_message})
        
        # Maintain max memory size
        if len(conversation_memory) > MAX_MEMORY:
            conversation_memory.pop(0)
        
        # Get chatbot response
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(chatbot_service.get_chat_response(user_message, conversation_memory))
        loop.close()
        
        # Add assistant response to memory
        conversation_memory.append({"role": "assistant", "content": response["message"]})
        
        return jsonify({
            "message": response["message"],
            "navigation": response["navigation"]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Chat error: {str(e)}")
        return jsonify({
            "error": "An error occurred while processing your message"
        }), 500 

@chat_bp.route('/system/message', methods=['POST'])
@login_required
def system_message():
    """Handle system event messages"""
    try:
        data = request.get_json()
        event_type = data.get('event_type')
        context = data.get('context')
        
        if not event_type:
            return jsonify({"error": "Event type is required"}), 400
            
        # Get AI response for system event
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        message = loop.run_until_complete(chatbot_service.get_system_message(event_type, context))
        loop.close()
        
        return jsonify({
            "message": message
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"System message error: {str(e)}")
        return jsonify({
            "error": "An error occurred while processing the system message"
        }), 500 