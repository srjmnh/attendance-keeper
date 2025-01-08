import os
import google.generativeai as genai
from flask import current_app

class GeminiService:
    _instance = None
    _conversation_memory = []
    _system_context = """You are Gemini, a helpful and somewhat witty (but polite) AI assistant for the AttendanceAI system.
    
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
            cls._instance = super(GeminiService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize Gemini service with API key"""
        if self._initialized:
            return
            
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('models/gemini-1.5-flash')
        
        # Start with system context
        self._conversation_memory = [
            {"role": "system", "content": self._system_context}
        ]
        self._initialized = True
    
    def _build_conversation(self):
        """Build conversation string from memory"""
        conv_str = ""
        for msg in self._conversation_memory:
            if msg["role"] == "system":
                conv_str += f"System: {msg['content']}
"
            elif msg["role"] == "user":
                conv_str += f"User: {msg['content']}
"
            else:
                conv_str += f"Assistant: {msg['content']}
"
        return conv_str
    
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
            
            response = self.model.generate_content(prompt)
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
            
            response = self.model.generate_content(prompt)
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
            
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            current_app.logger.error(f"Error getting student recommendations: {str(e)}")
            return "Sorry, I couldn't generate recommendations at this moment."
    
    def chat_with_assistant(self, user_message, context=None):
        """General chat interface with context awareness"""
        try:
            # Add user message to memory
            self._conversation_memory.append({"role": "user", "content": user_message})
            
            # Build conversation context
            conversation = self._build_conversation()
            if context:
                conversation = f"Additional Context: {context}

{conversation}"
            
            # Get AI response
            response = self.model.generate_content(conversation)
            
            # Add AI response to memory
            self._conversation_memory.append({"role": "assistant", "content": response.text})
            
            # Trim memory if too long (keep last 20 messages)
            if len(self._conversation_memory) > 21:  # 20 + 1 system message
                self._conversation_memory = [self._conversation_memory[0]] + self._conversation_memory[-20:]
            
            return response.text
        except Exception as e:
            current_app.logger.error(f"Error in chat: {str(e)}")
            return "Sorry, I encountered an error. Please try again." # Test comment
