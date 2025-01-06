import os
import google.generativeai as genai
import logging

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        """Initialize Gemini AI service"""
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        self.chat = None
        self._init_chat()

    def _init_chat(self):
        """Initialize chat with context"""
        context = """You are a helpful assistant for the attendance management system.
        You can help with:
        1. Finding attendance records
        2. Explaining attendance policies
        3. Troubleshooting face recognition issues
        4. Providing statistics and reports
        5. General system usage guidance
        
        Please be concise and professional in your responses."""
        
        try:
            self.chat = self.model.start_chat(history=[])
            self.chat.send_message(context)
        except Exception as e:
            logger.error(f"Error initializing chat: {str(e)}")
            raise

    def get_response(self, message, user_role='student'):
        """Get AI response for user message"""
        try:
            if not self.chat:
                self._init_chat()

            # Add role context to the message
            contextualized_message = f"[User Role: {user_role}] {message}"
            
            response = self.chat.send_message(contextualized_message)
            return response.text

        except Exception as e:
            logger.error(f"Error getting AI response: {str(e)}")
            return "I apologize, but I'm having trouble processing your request right now. Please try again later."

    def analyze_attendance_pattern(self, attendance_data):
        """Analyze attendance pattern and provide insights"""
        try:
            # Format attendance data for analysis
            data_str = "Attendance Pattern Analysis:\n"
            for record in attendance_data:
                data_str += f"Date: {record['date']}, Status: {record['status']}\n"
            
            prompt = f"""Analyze the following attendance pattern and provide insights:
            {data_str}
            
            Please provide:
            1. Overall attendance percentage
            2. Pattern of absences (if any)
            3. Recommendations for improvement (if needed)
            4. Any concerning trends
            
            Keep the response concise and actionable."""
            
            response = self.model.generate_content(prompt)
            return response.text

        except Exception as e:
            logger.error(f"Error analyzing attendance pattern: {str(e)}")
            return "Unable to analyze attendance pattern at this time."

    def generate_report_summary(self, report_data):
        """Generate a summary of attendance report"""
        try:
            # Format report data
            data_str = "Report Summary:\n"
            for key, value in report_data.items():
                data_str += f"{key}: {value}\n"
            
            prompt = f"""Generate a concise summary of the following attendance report:
            {data_str}
            
            Focus on:
            1. Key metrics
            2. Notable patterns
            3. Areas requiring attention
            
            Keep it brief and highlight the most important points."""
            
            response = self.model.generate_content(prompt)
            return response.text

        except Exception as e:
            logger.error(f"Error generating report summary: {str(e)}")
            return "Unable to generate report summary at this time."

    def get_troubleshooting_steps(self, issue_type, error_message=None):
        """Get troubleshooting steps for common issues"""
        try:
            prompt = f"""Provide troubleshooting steps for the following {issue_type} issue:
            Error: {error_message if error_message else 'No specific error message provided'}
            
            Please provide:
            1. Possible causes
            2. Step-by-step resolution steps
            3. Prevention tips
            
            Keep the response practical and easy to follow."""
            
            response = self.model.generate_content(prompt)
            return response.text

        except Exception as e:
            logger.error(f"Error getting troubleshooting steps: {str(e)}")
            return "Unable to provide troubleshooting steps at this time." 