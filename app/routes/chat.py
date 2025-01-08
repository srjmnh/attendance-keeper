from flask import Blueprint, render_template, request, jsonify, current_app, url_for
from flask_login import login_required, current_user
import openai
import os

bp = Blueprint('chat', __name__, url_prefix='/chat')

# System message that gives context about our application
SYSTEM_MESSAGE = """You are an AI assistant for the AttendanceAI system, a face recognition-based attendance management system. Here are your key functions:

1. Help users navigate the system:
   - Take Attendance (/attendance): Use face recognition to mark attendance
   - View Attendance (/attendance/view): View and manage attendance records
   - Register Students (/students/register): Register new students with face recognition
   - Manage Students (/students): View and manage student records

2. Explain features:
   - Face Recognition: Automatically mark attendance using webcam
   - Attendance Management: View, edit, and export attendance records
   - Student Registration: Register students with photos and details
   - Role-based Access: Different features for admin, teachers, and students

3. Guide users through common tasks:
   - Taking attendance using face recognition
   - Viewing and filtering attendance records
   - Exporting attendance to Excel
   - Registering new students
   - Managing student records

Always be helpful and provide direct links to relevant pages when possible."""

@bp.route('/')
@login_required
def index():
    """Chat interface"""
    return render_template('chat/index.html')

@bp.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400

        # Initialize OpenAI client
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        # Create chat completion
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": f"User Role: {current_user.role}\nMessage: {message}"}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        # Extract assistant's response
        assistant_message = response.choices[0].message.content
        
        return jsonify({
            'response': assistant_message,
            'role': current_user.role
        })
        
    except Exception as e:
        current_app.logger.error(f"Chat error: {str(e)}")
        return jsonify({'error': str(e)}), 500 