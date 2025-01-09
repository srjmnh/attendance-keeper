from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
from app.services.chatbot_service import ChatbotService
import asyncio

bp = Blueprint('ai', __name__)
chatbot_service = ChatbotService()

@bp.route('/api/ai/chat', methods=['POST'])
@login_required
def chat():
    """Chat with AI assistant"""
    try:
        data = request.get_json()
        message = data.get('message') or data.get('prompt')
        
        if not message:
            return jsonify({"error": "Message is required"}), 400
        
        # Get AI response using ChatbotService
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        response = loop.run_until_complete(chatbot_service.get_chat_response(message, []))
        loop.close()
        
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error in chat: {str(e)}")
        return jsonify({"error": str(e)}), 500 
