import os
import google.generativeai as genai
from datetime import datetime
from flask import current_app

class ChatbotService:
    """Service for handling chatbot interactions using Google's Gemini API"""
    
    def __init__(self):
        """Initialize Gemini client and system context"""
        api_key = os.getenv('GEMINI_API_KEY')  # Using your environment variable name
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
            
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-pro")
        
        # System context describing the attendance system
        self.system_context = """You are an AI assistant for a Facial Recognition Attendance System. Here are the key features you should know about:

1. Registration (Register Tab):
   - Teachers/admins can register students with their photo
   - Required fields: Name, Student ID, Class, Division
   - System uses AWS Rekognition to index faces

2. Recognition (Recognize Tab):
   - Upload photos to mark attendance
   - Can handle multiple faces in one photo
   - Uses AWS Rekognition to match faces
   - Automatically marks attendance for recognized students

3. Subjects (Subjects Tab):
   - Manage different subjects
   - Add new subjects
   - View existing subjects

4. Attendance (Attendance Tab):
   - View attendance records
   - Filter by student ID, subject, date range
   - Edit attendance records inline
   - Download/upload attendance as Excel

Navigation Commands:
- To show Register tab: #show-register
- To show Recognize tab: #show-recognize
- To show Subjects tab: #show-subjects
- To show Attendance tab: #show-attendance

Your role is to:
1. Answer questions about system features
2. Guide users through processes
3. Troubleshoot common issues
4. Use navigation commands when relevant
5. Be friendly and helpful

When suggesting navigation, use the exact commands (e.g., "#show-register") as they trigger UI actions."""

    async def get_chat_response(self, user_message, conversation_history):
        """Get response from Gemini API"""
        try:
            # Build conversation string
            conv_str = f"System: {self.system_context}\n\n"
            
            # Add conversation history
            for msg in conversation_history:
                role = "User" if msg["role"] == "user" else "Assistant"
                conv_str += f"{role}: {msg['content']}\n"
            
            # Add the current message
            conv_str += f"User: {user_message}\n"
            
            # Log request for debugging
            current_app.logger.info("Sending request to Gemini API")
            
            # Call Gemini API
            response = self.model.generate_content(conv_str)
            
            if not response.text:
                return {
                    "message": "I'm having trouble generating a response. Please try again.",
                    "navigation": None
                }
            
            # Get response text
            message_content = response.text.strip()
            
            return {
                "message": message_content,
                "navigation": self._extract_navigation_command(message_content)
            }
            
        except Exception as e:
            current_app.logger.error(f"Gemini API error: {str(e)}")
            return {
                "message": "I'm currently experiencing technical difficulties. Please try again later.",
                "navigation": None
            }

    def _extract_navigation_command(self, message):
        """Extract navigation command from message if present"""
        navigation_commands = {
            "#show-register": "register",
            "#show-recognize": "recognize",
            "#show-subjects": "subjects",
            "#show-attendance": "attendance"
        }
        
        for command, tab in navigation_commands.items():
            if command in message:
                return tab
        
        return None 