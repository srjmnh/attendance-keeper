"""AI service using Google's Gemini for advanced features"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import google.generativeai as genai
from flask import current_app
from firebase_admin import firestore

class AIService:
    """Service for AI-powered features using Gemini"""

    # Chat memory configuration
    MAX_MEMORY = 20
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

    def __init__(self):
        """Initialize the AI service"""
        try:
            genai.configure(api_key=current_app.config.get('GEMINI_API_KEY'))
            self.model = genai.GenerativeModel(
                model_name=current_app.config.get('GEMINI_MODEL', 'models/gemini-1.5-flash'),
                generation_config={
                    'temperature': current_app.config.get('GEMINI_TEMPERATURE', 0.7),
                    'top_p': current_app.config.get('GEMINI_TOP_P', 0.95),
                    'top_k': current_app.config.get('GEMINI_TOP_K', 40)
                }
            )
            self.conversation_memory = [{"role": "system", "content": self.system_context}]
            self.db = firestore.client()
            self.logger = logging.getLogger(__name__)
            self.initialized = True
        except Exception as e:
            self.logger.error(f"Failed to initialize AI service: {str(e)}")
            self.initialized = False

    def process_chat(
        self,
        message: str,
        context: Dict,
        conversation_id: Optional[str] = None
    ) -> Dict:
        """Process chat messages with context-aware responses"""
        if not self.initialized:
            return {'error': 'AI service not properly initialized'}
            
        try:
            # Add user message to memory
            self.conversation_memory.append({"role": "user", "content": message})

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
                assistant_reply = "Hmm, I'm having trouble responding right now."
            else:
                parts = response.candidates[0].content.parts
                assistant_reply = "".join(part.text for part in parts).strip()

            # Add assistant reply to memory
            self.conversation_memory.append({"role": "assistant", "content": assistant_reply})

            # Trim memory if too long
            if len(self.conversation_memory) > self.MAX_MEMORY:
                self.conversation_memory.pop(1)  # Keep system message, remove oldest user message

            # Extract suggestions and insights
            suggestions = self._extract_suggestions(assistant_reply)
            insights = self._extract_insights(assistant_reply)

            # Save conversation if ID provided
            if conversation_id:
                self._save_conversation(conversation_id, message, assistant_reply)

            return {
                'message': assistant_reply,
                'conversation_id': conversation_id,
                'suggestions': suggestions,
                'insights': insights
            }

        except Exception as e:
            self.logger.error(f"Error processing chat: {str(e)}")
            return {'error': str(e)}

    def _get_conversation_history(self, conversation_id: str) -> List[Dict]:
        """Get conversation history from Firestore"""
        try:
            # Get conversation document
            conversation_ref = self.db.collection('conversations').document(conversation_id)
            conversation = conversation_ref.get()

            if not conversation.exists:
                return []

            # Get messages subcollection
            messages = (conversation_ref
                .collection('messages')
                .order_by('timestamp', direction=firestore.Query.ASCENDING)
                .limit(10)  # Limit to last 10 messages
                .stream())

            history = []
            for message in messages:
                data = message.to_dict()
                history.append({
                    'role': data['role'],
                    'parts': [data['content']],
                    'timestamp': data['timestamp']
                })

            return history

        except Exception as e:
            self.logger.error(f"Error getting conversation history: {str(e)}")
            return []

    def _save_conversation(
        self,
        conversation_id: str,
        message: str,
        response: str
    ) -> None:
        """Save conversation to Firestore"""
        try:
            # Get conversation document reference
            conversation_ref = self.db.collection('conversations').document(conversation_id)
            
            # Create conversation if it doesn't exist
            if not conversation_ref.get().exists:
                conversation_ref.set({
                    'created_at': firestore.SERVER_TIMESTAMP,
                    'updated_at': firestore.SERVER_TIMESTAMP,
                    'message_count': 0
                })

            # Get messages subcollection reference
            messages_ref = conversation_ref.collection('messages')
            
            # Add user message
            messages_ref.add({
                'role': 'user',
                'content': message,
                'timestamp': firestore.SERVER_TIMESTAMP
            })
            
            # Add assistant response
            messages_ref.add({
                'role': 'assistant',
                'content': response,
                'timestamp': firestore.SERVER_TIMESTAMP
            })
            
            # Update conversation metadata
            conversation_ref.update({
                'updated_at': firestore.SERVER_TIMESTAMP,
                'message_count': firestore.Increment(2)
            })

        except Exception as e:
            self.logger.error(f"Error saving conversation: {str(e)}")

    def analyze_attendance_patterns(self, records: List[Dict]) -> Dict:
        """Analyze attendance patterns and provide insights"""
        try:
            # Prepare data for analysis
            data = json.dumps(records, indent=2)
            prompt = f"""
            Analyze these attendance records and provide insights:
            1. Attendance trends and patterns
            2. Potential issues or concerns
            3. Recommendations for improvement
            4. Notable achievements or positive trends

            Records:
            {data}
            """

            response = self.model.generate_content(prompt)
            return self._parse_analysis_response(response.text)

        except Exception as e:
            self.logger.error(f"Error analyzing attendance: {str(e)}")
            return {'error': str(e)}

    def analyze_student_patterns(self, student_data: Dict) -> Dict:
        """Analyze individual student patterns"""
        try:
            data = json.dumps(student_data, indent=2)
            prompt = f"""
            Analyze this student's attendance and performance:
            1. Attendance patterns and consistency
            2. Subject-wise participation
            3. Areas of improvement
            4. Personalized recommendations

            Student Data:
            {data}
            """

            response = self.model.generate_content(prompt)
            return self._parse_analysis_response(response.text)

        except Exception as e:
            self.logger.error(f"Error analyzing student: {str(e)}")
            return {'error': str(e)}

    def suggest_schedule_optimization(self, subject_data: Dict, context: Dict) -> Dict:
        """Suggest optimal scheduling based on attendance patterns"""
        try:
            data = json.dumps({**subject_data, **context}, indent=2)
            prompt = f"""
            Analyze this subject's data and suggest optimal scheduling:
            1. Best days/times for classes based on attendance
            2. Factors affecting attendance
            3. Schedule optimization recommendations
            4. Implementation steps

            Data:
            {data}
            """

            response = self.model.generate_content(prompt)
            return self._parse_suggestions_response(response.text)

        except Exception as e:
            self.logger.error(f"Error suggesting schedule: {str(e)}")
            return {'error': str(e)}

    def predict_attendance_risk(self, student_data: Dict) -> Dict:
        """Predict attendance risk and suggest interventions"""
        try:
            data = json.dumps(student_data, indent=2)
            prompt = f"""
            Analyze this student's data and predict attendance risks:
            1. Risk factors and patterns
            2. Likelihood of future attendance issues
            3. Early intervention suggestions
            4. Support strategies

            Student Data:
            {data}
            """

            response = self.model.generate_content(prompt)
            return {
                'risk_analysis': self._parse_analysis_response(response.text),
                'risk_level': self._calculate_risk_level(student_data)
            }

        except Exception as e:
            self.logger.error(f"Error predicting risk: {str(e)}")
            return {'error': str(e)}

    def generate_personalized_report(
        self,
        student_data: Dict,
        attendance_data: List[Dict],
        report_type: str = 'summary'
    ) -> Dict:
        """Generate personalized attendance reports"""
        try:
            data = {
                'student': student_data,
                'attendance': attendance_data,
                'type': report_type
            }
            prompt = f"""
            Generate a personalized attendance report:
            1. Overall attendance summary
            2. Subject-wise analysis
            3. Progress and improvements
            4. Recommendations and next steps

            Data:
            {json.dumps(data, indent=2)}
            """

            response = self.model.generate_content(prompt)
            return {
                'report': response.text,
                'insights': self._extract_insights(response.text),
                'recommendations': self._extract_recommendations(response.text)
            }

        except Exception as e:
            self.logger.error(f"Error generating report: {str(e)}")
            return {'error': str(e)}

    def suggest_engagement_strategies(self, context: Dict) -> Dict:
        """Suggest strategies to improve student engagement"""
        try:
            prompt = f"""
            Suggest strategies to improve student engagement:
            1. Interactive learning methods
            2. Attendance motivation techniques
            3. Communication strategies
            4. Technology integration ideas

            Context:
            {json.dumps(context, indent=2)}
            """

            response = self.model.generate_content(prompt)
            return self._parse_suggestions_response(response.text)

        except Exception as e:
            self.logger.error(f"Error suggesting strategies: {str(e)}")
            return {'error': str(e)}

    def _build_context_prompt(self, context: Dict) -> str:
        """Build context-aware prompt for chat"""
        role_prompts = {
            'student': "You are assisting a student with their attendance and academic progress.",
            'teacher': "You are assisting a teacher with class management and student engagement.",
            'admin': "You are assisting an administrator with system-wide attendance management."
        }

        base_prompt = role_prompts.get(
            context.get('user_role', 'student'),
            role_prompts['student']
        )

        return f"{base_prompt}\n\nContext: {json.dumps(context, indent=2)}"

    def _parse_analysis_response(self, response: str) -> Dict:
        """Parse analysis response into structured format"""
        try:
            sections = response.split('\n\n')
            return {
                'analysis': sections[0] if sections else response,
                'recommendations': sections[1] if len(sections) > 1 else None
            }
        except Exception:
            return {'analysis': response}

    def _parse_suggestions_response(self, response: str) -> Dict:
        """Parse suggestions response into structured format"""
        try:
            sections = response.split('\n\n')
            return {
                'suggestions': sections[0] if sections else response,
                'rationale': sections[1] if len(sections) > 1 else None,
                'implementation_steps': sections[2] if len(sections) > 2 else None
            }
        except Exception:
            return {'suggestions': response}

    def _extract_suggestions(self, text: str) -> List[str]:
        """Extract actionable suggestions from text"""
        try:
            lines = text.split('\n')
            suggestions = []
            for line in lines:
                if any(word in line.lower() for word in ['suggest', 'recommend', 'try', 'consider']):
                    suggestions.append(line.strip())
            return suggestions
        except Exception:
            return []

    def _extract_insights(self, text: str) -> List[str]:
        """Extract key insights from text"""
        try:
            lines = text.split('\n')
            insights = []
            for line in lines:
                if any(word in line.lower() for word in ['notice', 'observe', 'find', 'appear']):
                    insights.append(line.strip())
            return insights
        except Exception:
            return []

    def _extract_recommendations(self, text: str) -> List[str]:
        """Extract specific recommendations from text"""
        try:
            lines = text.split('\n')
            recommendations = []
            for line in lines:
                if line.strip().startswith(('- ', '* ', '1. ')):
                    recommendations.append(line.strip())
            return recommendations
        except Exception:
            return []

    def _calculate_risk_level(self, student_data: Dict) -> str:
        """Calculate attendance risk level"""
        try:
            attendance_rate = student_data.get('attendance_rate', 0)
            if attendance_rate >= 90:
                return 'low'
            elif attendance_rate >= 75:
                return 'medium'
            else:
                return 'high'
        except Exception:
            return 'unknown' 