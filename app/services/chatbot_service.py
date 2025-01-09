import os
from openai import OpenAI
from datetime import datetime
from flask import current_app

class ChatbotService:
    """Service for handling chatbot interactions using OpenAI"""
    
    def __init__(self):
        """Initialize OpenAI client and system context"""
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
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
        """Get response from OpenAI ChatGPT"""
        try:
            # Prepare the messages including system context and history
            messages = [
                {"role": "system", "content": self.system_context}
            ]
            
            # Add conversation history
            for msg in conversation_history:
                messages.append({
                    "role": "user" if msg["role"] == "user" else "assistant",
                    "content": msg["content"]
                })
            
            # Add the current message
            messages.append({"role": "user", "content": user_message})
            
            # Get response from OpenAI
            completion = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            # Extract and return the response
            if completion.choices:
                return {
                    "message": completion.choices[0].message.content,
                    "navigation": self._extract_navigation_command(completion.choices[0].message.content)
                }
            
            return {
                "message": "I'm having trouble generating a response. Please try again.",
                "navigation": None
            }
            
        except Exception as e:
            current_app.logger.error(f"OpenAI API error: {str(e)}")
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