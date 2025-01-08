import os
from openai import OpenAI
from flask import current_app

class OpenAIService:
    _instance = None
    _conversation_memory = []
    _system_context = """You are an AI assistant for the AttendanceAI system.
    
Features you can help with:
1. Facial Recognition Attendance:
   - Student registration with face photos
   - Taking attendance by recognizing faces
   - Managing student records
   
2. Attendance Management:
   - Viewing and filtering attendance records
   - Downloading attendance reports
   - Analyzing attendance patterns
   
3. Subject Management:
   - Adding and managing subjects
   - Assigning subjects to classes
   
4. User Roles:
   - Admin: Full system access
   - Teacher: Attendance and subject management
   - Student: View own attendance
   
You can help users understand these features, troubleshoot issues, and provide insights from attendance data.
Always be helpful, clear, and maintain a friendly tone."""
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OpenAIService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize OpenAI service with API key"""
        if self._initialized:
            return
            
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        # Initialize the OpenAI client with the API key
        self.client = OpenAI(api_key=api_key)
        self._initialized = True
        
        # Initialize conversation with system message
        self._conversation_memory = [{"role": "system", "content": self._system_context}]
    
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
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self._system_context},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            current_app.logger.error(f"Error analyzing attendance: {str(e)}")
            return "Sorry, I could not analyze the attendance data at this moment."

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
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self._system_context},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            current_app.logger.error(f"Error generating report summary: {str(e)}")
            return "Sorry, I could not generate the report summary at this moment."
    
    def get_student_recommendations(self, student_data):
        """Get personalized recommendations for a student"""
        try:
            prompt = f"""
            Based on this student attendance data:
            {student_data}
            
            Provide:
            1. Personalized attendance analysis
            2. Specific recommendations for improvement
            3. Potential risk factors
            4. Suggested support measures
            
            Keep the tone supportive and constructive.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self._system_context},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            current_app.logger.error(f"Error getting student recommendations: {str(e)}")
            return "Sorry, I could not generate recommendations at this moment."

    def chat_with_assistant(self, user_message, context=None):
        """General chat interface with context awareness"""
        try:
            if context:
                user_message = f"Context: {context}\n\nUser: {user_message}"
            
            # Add user message to conversation
            self._conversation_memory.append({"role": "user", "content": user_message})
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=self._conversation_memory,
                max_tokens=1000,
                temperature=0.7
            )
            
            assistant_reply = response.choices[0].message.content.strip()
            
            # Add assistant reply to conversation memory
            self._conversation_memory.append({"role": "assistant", "content": assistant_reply})
            
            # Trim memory if too long (keep system message and last 19 messages)
            if len(self._conversation_memory) > 20:  # 19 + 1 system message
                self._conversation_memory = [self._conversation_memory[0]] + self._conversation_memory[-19:]
            
            return assistant_reply
        except Exception as e:
            current_app.logger.error(f"Error in chat: {str(e)}")
            return "Sorry, I encountered an error. Please try again." 