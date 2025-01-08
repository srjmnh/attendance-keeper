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