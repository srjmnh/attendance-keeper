from flask import Blueprint, request, jsonify
from flask_login import login_required
import google.generativeai as genai
import os
import logging

chat = Blueprint('chat', __name__)
logger = logging.getLogger(__name__)

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY environment variable not set.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-1.5-flash")

# Chat memory
MAX_MEMORY = 20
conversation_memory = []

# System context
system_context = """You are Gemini, a somewhat witty (but polite) AI assistant.
Facial Recognition Attendance system features:

1) AWS Rekognition:
   - We keep a 'students' collection on startup.
   - /register indexes a face by (name + student_id).
   - /recognize detects faces in an uploaded image, logs attendance in Firestore if matched.

2) Attendance:
   - Firestore 'attendance' collection: { student_id, name, timestamp, subject_id, subject_name, status='PRESENT' }.
   - UI has tabs: Register, Recognize, Subjects, Attendance (Bootstrap + DataTables).
   - Attendance can filter, inline-edit, download/upload Excel.

3) Subjects:
   - We can add subjects to 'subjects' collection, referenced in recognition.

4) Multi-Face:
   - If multiple recognized faces, each is logged to attendance.

5) Chat:
   - You are the assistant, a bit humorous, guiding usage or code features.
"""

# Start the conversation with a system message
conversation_memory.append({"role": "system", "content": system_context})

@chat.route('/process_prompt', methods=['POST'])
@login_required
def process_prompt():
    """Process chat prompts using Gemini"""
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({"error": "No prompt provided"}), 400

        user_prompt = data['prompt']
        
        # Add user message to memory
        conversation_memory.append({"role": "user", "content": user_prompt})
        
        # Keep only last MAX_MEMORY messages
        if len(conversation_memory) > MAX_MEMORY:
            conversation_memory.pop(1)  # Remove oldest message after system context
        
        # Create chat and get response
        chat = model.start_chat(history=[
            (msg["content"], None) if msg["role"] == "system" else 
            (msg["content"], None) if msg["role"] == "user" else 
            (None, msg["content"]) 
            for msg in conversation_memory
        ])
        
        response = chat.send_message(user_prompt)
        
        # Add assistant response to memory
        conversation_memory.append({"role": "assistant", "content": response.text})
        
        return jsonify({"message": response.text})
        
    except Exception as e:
        logger.error(f"Error processing chat prompt: {str(e)}")
        return jsonify({"error": str(e)}), 500 