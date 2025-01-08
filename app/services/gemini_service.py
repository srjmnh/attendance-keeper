<<<<<<< HEAD
import os
import google.generativeai as genai
from typing import List, Dict

class GeminiService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        
        genai.configure(api_key=self.api_key)
        # If you do NOT have access to "gemini-1.5-flash", switch to "models/chat-bison-001"
        self.model = genai.GenerativeModel("models/gemini-1.5-flash")
        
        # Chat memory
        self.MAX_MEMORY = 20
        self.conversation_memory: List[Dict[str, str]] = []
        
        # System context
        self.system_context = """You are Gemini, a somewhat witty (but polite) AI assistant.
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
        self.conversation_memory.append({"role": "system", "content": self.system_context})

    def process_prompt(self, user_prompt: str) -> str:
        if not user_prompt.strip():
            return "I didn't receive any message. What would you like to know about the attendance system?"

        # Add user message
        self.conversation_memory.append({"role": "user", "content": user_prompt})

        # Build conversation string
        conv_str = ""
        for msg in self.conversation_memory:
            if msg["role"] == "system":
                conv_str += f"System: {msg['content']}\n"
            elif msg["role"] == "user":
                conv_str += f"User: {msg['content']}\n"
            else:
                conv_str += f"Assistant: {msg['content']}\n"

        # Call Gemini
        try:
            response = self.model.generate_content(conv_str)
        except Exception as e:
            assistant_reply = f"Error generating response: {str(e)}"
        else:
            if not response.candidates:
                assistant_reply = "Hmm, I'm having trouble responding right now."
            else:
                parts = response.candidates[0].content.parts
                assistant_reply = "".join(part.text for part in parts).strip()

        # Add assistant reply
        self.conversation_memory.append({"role": "assistant", "content": assistant_reply})

        if len(self.conversation_memory) > self.MAX_MEMORY:
            self.conversation_memory.pop(0)

        return assistant_reply 
=======
# Gemini AI Service for chat and analysis
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
            
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        
        # Configure the model
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 2048,
        }
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        
        self.model = genai.GenerativeModel(
            model_name="gemini-pro",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        # Initialize chat
        self.chat = self.model.start_chat(history=[])
        self.chat.send_message(self._system_context)
        
        self._initialized = True
    
    def _build_conversation(self):
        """Build conversation string from memory"""
        try:
            conversation = []
            for msg in self._conversation_memory:
                if msg["role"] == "system":
                    conversation.append({"role": "user", "parts": [msg["content"]]})
                elif msg["role"] == "user":
                    conversation.append({"role": "user", "parts": [msg["content"]]})
                else:
                    conversation.append({"role": "model", "parts": [msg["content"]]})
            return conversation
        except Exception as e:
            current_app.logger.error(f"Error building conversation: {str(e)}")
            return []
    
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
            if response.prompt_feedback.block_reason:
                return "Sorry, I cannot analyze this content due to safety concerns."
            return response.text
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
            
            response = self.model.generate_content(prompt)
            if response.prompt_feedback.block_reason:
                return "Sorry, I cannot analyze this content due to safety concerns."
            return response.text
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
            
            response = self.model.generate_content(prompt)
            if response.prompt_feedback.block_reason:
                return "Sorry, I cannot analyze this content due to safety concerns."
            return response.text
        except Exception as e:
            current_app.logger.error(f"Error getting student recommendations: {str(e)}")
            return "Sorry, I could not generate recommendations at this moment."
    
    def chat_with_assistant(self, user_message, context=None):
        """General chat interface with context awareness"""
        try:
            if context:
                user_message = f"Context: {context}\n\nUser: {user_message}"
            
            # Send message to chat
            response = self.chat.send_message(user_message)
            
            if response.prompt_feedback.block_reason:
                return "I apologize, but I cannot respond to that due to safety concerns."
            
            # Add to conversation memory
            self._conversation_memory.append({"role": "user", "content": user_message})
            self._conversation_memory.append({"role": "assistant", "content": response.text})
            
            # Trim memory if too long (keep last 20 messages)
            if len(self._conversation_memory) > 21:  # 20 + 1 system message
                self._conversation_memory = [self._conversation_memory[0]] + self._conversation_memory[-20:]
            
            return response.text
        except Exception as e:
            current_app.logger.error(f"Error in chat: {str(e)}")
            return "Sorry, I encountered an error. Please try again."
>>>>>>> modernize-ui
