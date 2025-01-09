from flask import Blueprint, jsonify, request, current_app
from app.services.chatbot_service import ChatbotService
import asyncio

bp = Blueprint('api', __name__, url_prefix='/api')

# Initialize conversation memory
MAX_MEMORY = 20
conversation_memory = []

@bp.route('/ai/chat', methods=['POST'])
async def chat():
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
        chatbot = ChatbotService()
        response = await chatbot.get_chat_response(user_message, conversation_memory)
        
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