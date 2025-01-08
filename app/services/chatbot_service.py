import google.generativeai as genai
from flask import current_app

class ChatbotService:
    def __init__(self):
        self.api_key = current_app.config['GEMINI_API_KEY']
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("models/gemini-1.5-flash")
        self.max_memory = 20
        self.conversation_memory = []
        self._initialize_context()
    
    def _initialize_context(self):
        """Initialize the chatbot with system context"""
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
        self.conversation_memory.append({"role": "system", "content": system_context})
    
    def process_message(self, user_message):
        """Process a user message and return the chatbot's response"""
        try:
            # Add user message to memory
            self.conversation_memory.append({"role": "user", "content": user_message})
            
            # Build conversation string
            conv_str = ""
            for msg in self.conversation_memory:
                if msg["role"] == "system":
                    conv_str += f"System: {msg['content']}\n"
                elif msg["role"] == "user":
                    conv_str += f"User: {msg['content']}\n"
                else:
                    conv_str += f"Assistant: {msg['content']}\n"
            
            # Generate response
            response = self.model.generate_content(conv_str)
            
            if not response.candidates:
                assistant_reply = "I'm having trouble responding right now."
            else:
                parts = response.candidates[0].content.parts
                assistant_reply = "".join(part.text for part in parts).strip()
            
            # Add assistant reply to memory
            self.conversation_memory.append({"role": "assistant", "content": assistant_reply})
            
            # Maintain max memory size
            if len(self.conversation_memory) > self.max_memory:
                # Keep system message and remove oldest messages
                system_msg = self.conversation_memory[0]
                self.conversation_memory = [system_msg] + self.conversation_memory[-self.max_memory+1:]
            
            return assistant_reply
        
        except Exception as e:
            return f"Error: {str(e)}" 