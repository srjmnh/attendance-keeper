import os
import google.generativeai as genai
from flask import current_app

class GeminiService:
    def __init__(self):
        """Initialize Gemini service with API key"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
        # Initialize chat history
        self.chat = self.model.start_chat(history=[])
    
    def analyze_attendance(self, attendance_data):
        """Analyze attendance data and provide insights"""
        try:
            prompt = f"""
            As an attendance analysis expert, analyze this attendance data and provide insights:
            {attendance_data}
            
            Please provide:
            1. Overall attendance patterns
            2. Students who need attention
            3. Recommendations for improvement
            4. Any notable trends
            
            Format the response in a clear, professional manner.
            """
            
            response = self.chat.send_message(prompt)
            return response.text
        except Exception as e:
            current_app.logger.error(f"Error analyzing attendance: {str(e)}")
            return "Sorry, I couldn't analyze the attendance data at this moment."
    
    def generate_report_summary(self, report_data):
        """Generate a summary of attendance reports"""
        try:
            prompt = f"""
            Generate a concise summary of this attendance report:
            {report_data}
            
            Focus on:
            - Key statistics
            - Important findings
            - Action items
            - Areas needing attention
            
            Make it clear and actionable.
            """
            
            response = self.chat.send_message(prompt)
            return response.text
        except Exception as e:
            current_app.logger.error(f"Error generating report summary: {str(e)}")
            return "Sorry, I couldn't generate the report summary at this moment."
    
    def get_student_recommendations(self, student_data):
        """Get personalized recommendations for a student"""
        try:
            prompt = f"""
            Based on this student's attendance data:
            {student_data}
            
            Provide:
            1. Personalized attendance analysis
            2. Specific recommendations for improvement
            3. Potential risk factors
            4. Suggested support measures
            
            Keep the tone supportive and constructive.
            """
            
            response = self.chat.send_message(prompt)
            return response.text
        except Exception as e:
            current_app.logger.error(f"Error getting student recommendations: {str(e)}")
            return "Sorry, I couldn't generate recommendations at this moment."
    
    def chat_with_assistant(self, user_message, context=None):
        """General chat interface with context awareness"""
        try:
            if context:
                prompt = f"""
                Context: {context}
                
                User Question: {user_message}
                
                Please provide a helpful response considering the context.
                """
            else:
                prompt = user_message
            
            response = self.chat.send_message(prompt)
            return response.text
        except Exception as e:
            current_app.logger.error(f"Error in chat: {str(e)}")
            return "Sorry, I encountered an error. Please try again." 