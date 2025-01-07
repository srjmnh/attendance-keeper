import os
import google.generativeai as genai
from flask import current_app

class GeminiAIService:
    """Service for interacting with Google's Gemini AI"""

    def __init__(self):
        """Initialize the Gemini AI service"""
        try:
            api_key = os.environ.get('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            
            # Set default parameters
            self.generation_config = {
                'temperature': 0.7,
                'top_p': 0.8,
                'top_k': 40,
                'max_output_tokens': 1024,
            }
            
        except Exception as e:
            current_app.logger.error(f"Error initializing Gemini AI service: {str(e)}")
            raise

    def get_response(self, message, context=None):
        """Get AI response for user message"""
        try:
            # Build prompt with context
            prompt = self._build_prompt(message, context)
            
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config=self.generation_config
            )
            
            return response.text
            
        except Exception as e:
            current_app.logger.error(f"Error getting AI response: {str(e)}")
            return "I apologize, but I encountered an error. Please try again later."

    def _build_prompt(self, message, context=None):
        """Build prompt with user context"""
        if not context:
            return message
            
        # Add role-specific context
        role = context.get('role', 'student')
        name = context.get('name', 'User')
        
        prompt = f"""You are an AI assistant for an attendance management system.
        You are talking to {name}, who is a {role}.
        
        Please provide helpful and relevant information based on their role.
        For students: Focus on attendance status, improvement suggestions, and study tips.
        For teachers: Focus on class management, attendance patterns, and teaching strategies.
        For admins: Focus on system-wide statistics, policy recommendations, and best practices.
        
        User's message: {message}
        """
        
        return prompt 