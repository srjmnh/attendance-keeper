import os
import google.generativeai as genai
from datetime import datetime
from flask import current_app, request

class ChatbotService:
    """Service for handling chatbot interactions using Google's Gemini API"""
    
    def __init__(self):
        """Initialize Gemini client and system context"""
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
            
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-pro")
        
        # Track current context
        self.current_page = None
        self.last_action = None
        self.page_data = {}
        
        # Define available actions
        self.actions = {
            'update_attendance': self._update_attendance_status,
            'update_student': self._update_student_details,
            'update_teacher': self._update_teacher_details
        }

    def _get_page_context(self):
        """Get context information for current page"""
        page_contexts = {
            'dashboard': """You are on the Dashboard page. Here you can:
- View overall attendance statistics
- Access quick navigation to all features
- See recent attendance records
- Start face recognition""",
            
            'attendance/view': """You are on the Attendance View page. Current context:
- Viewing attendance records
- Can filter by date, student, or subject
- Can modify attendance status
- Total records: {record_count}
- Current date: {current_date}""",
            
            'admin/manage/students': """You are on the Student Management page. Current context:
- Managing student records
- Total students: {student_count}
- Can add/edit/delete students
- Can update student details (name, ID, class, division)""",
            
            'admin/manage/teachers': """You are on the Teacher Management page. Current context:
- Managing teacher records
- Total teachers: {teacher_count}
- Can add/edit/delete teachers
- Can assign subjects and classes""",
            
            'recognition/classroom': """You are on the Face Recognition page. Current context:
- Camera is {camera_status}
- Face detection is {detection_status}
- Processing interval: 2-3 seconds
- Can mark attendance in real-time""",
            
            'recognition/register': """You are on the Student Registration page. Here you can:
- Register new students with photos
- Required fields: Name, Student ID, Class, Division
- System will index face for recognition
- Photos should have clear face visibility"""
        }
        
        # Get current page from request
        current_path = request.path.lstrip('/')
        self.current_page = current_path
        
        # Get base context for current page
        context = page_contexts.get(current_path, "You are on the AttendanceAI system.")
        
        # Add dynamic data
        if current_path == 'attendance/view':
            context = context.format(
                record_count=self.page_data.get('record_count', 'unknown'),
                current_date=datetime.now().strftime('%Y-%m-%d')
            )
        elif current_path == 'admin/manage/students':
            context = context.format(
                student_count=self.page_data.get('student_count', 'unknown')
            )
        elif current_path == 'admin/manage/teachers':
            context = context.format(
                teacher_count=self.page_data.get('teacher_count', 'unknown')
            )
        elif current_path == 'recognition/classroom':
            context = context.format(
                camera_status=self.page_data.get('camera_status', 'inactive'),
                detection_status=self.page_data.get('detection_status', 'inactive')
            )
            
        return context

    def update_page_data(self, data):
        """Update current page data"""
        self.page_data.update(data)

    async def _update_attendance_status(self, student_id, date, status):
        """Update attendance status for a student"""
        try:
            # Get attendance record
            attendance_ref = current_app.db.collection('attendance')
            query = attendance_ref.where('student_id', '==', student_id).where('date', '==', date)
            records = query.get()
            
            if not records:
                return "No attendance record found for this student on the specified date."
                
            # Update status
            record = records[0]
            attendance_ref.document(record.id).update({'status': status})
            return f"Updated attendance status to {status} for student {student_id} on {date}"
            
        except Exception as e:
            current_app.logger.error(f"Error updating attendance: {str(e)}")
            return "Failed to update attendance status."

    async def _update_student_details(self, student_id, updates):
        """Update student details"""
        try:
            # Get student record
            users_ref = current_app.db.collection('users')
            query = users_ref.where('student_id', '==', student_id).where('role', '==', 'student')
            students = query.get()
            
            if not students:
                return "Student not found."
                
            # Update details
            student = students[0]
            users_ref.document(student.id).update(updates)
            return f"Updated student {student_id} details: {updates}"
            
        except Exception as e:
            current_app.logger.error(f"Error updating student: {str(e)}")
            return "Failed to update student details."

    async def _update_teacher_details(self, teacher_id, updates):
        """Update teacher details"""
        try:
            # Get teacher record
            users_ref = current_app.db.collection('users')
            query = users_ref.where('teacher_id', '==', teacher_id).where('role', '==', 'teacher')
            teachers = query.get()
            
            if not teachers:
                return "Teacher not found."
                
            # Update details
            teacher = teachers[0]
            users_ref.document(teacher.id).update(updates)
            return f"Updated teacher {teacher_id} details: {updates}"
            
        except Exception as e:
            current_app.logger.error(f"Error updating teacher: {str(e)}")
            return "Failed to update teacher details."

    async def _extract_action_request(self, message):
        """Extract action request from message"""
        try:
            # Create action extraction prompt with more explicit examples
            prompt = f"""Extract action request from this message. Be precise and exact.
            Message: {message}
            
            Valid actions and formats:
            1. Update attendance status:
               Format: {{"action": "update_attendance", "params": {{"student_id": "123", "date": "YYYY-MM-DD", "status": "present/absent"}}}}
               Examples: 
               - "mark student 210 as present today" -> {{"action": "update_attendance", "params": {{"student_id": "210", "date": "2025-01-13", "status": "present"}}}}
               - "change attendance for 350 to absent" -> {{"action": "update_attendance", "params": {{"student_id": "350", "date": "2025-01-13", "status": "absent"}}}}
            
            2. Update student details:
               Format: {{"action": "update_student", "params": {{"student_id": "123", "updates": {{"name": "New Name", "class": "4", "division": "A"}}}}}}
               Examples:
               - "update student 210 name to John" -> {{"action": "update_student", "params": {{"student_id": "210", "updates": {{"name": "John"}}}}}}
               - "change class of student 350 to 4A" -> {{"action": "update_student", "params": {{"student_id": "350", "updates": {{"class": "4", "division": "A"}}}}}}
            
            3. Update teacher details:
               Format: {{"action": "update_teacher", "params": {{"teacher_id": "123", "updates": {{"name": "New Name", "subjects": ["Math", "Science"]}}}}}}
               Examples:
               - "update teacher T001 name to Sarah" -> {{"action": "update_teacher", "params": {{"teacher_id": "T001", "updates": {{"name": "Sarah"}}}}}}
               - "set teacher T002 subjects to Math and Science" -> {{"action": "update_teacher", "params": {{"teacher_id": "T002", "updates": {{"subjects": ["Math", "Science"]}}}}}}
            
            If the message matches any of these patterns, return the corresponding action format.
            If no match is found or the message is unclear, return null.
            Use today's date (2025-01-13) for attendance if no date is specified."""
            
            response = self.model.generate_content(prompt)
            if not response.text:
                return None
                
            # Parse action request with better error handling
            try:
                action_request = eval(response.text.strip())
                if not action_request:
                    return None
                    
                if not isinstance(action_request, dict):
                    return None
                    
                if 'action' not in action_request or 'params' not in action_request:
                    return None
                    
                if action_request['action'] not in self.actions:
                    return None
                    
                # Validate parameters based on action type
                params = action_request['params']
                if action_request['action'] == 'update_attendance':
                    if not all(k in params for k in ['student_id', 'date', 'status']):
                        return None
                elif action_request['action'] == 'update_student':
                    if not all(k in params for k in ['student_id', 'updates']):
                        return None
                elif action_request['action'] == 'update_teacher':
                    if not all(k in params for k in ['teacher_id', 'updates']):
                        return None
                        
                return action_request
                
            except Exception as e:
                current_app.logger.error(f"Error parsing action request: {str(e)}")
                return None
            
        except Exception as e:
            current_app.logger.error(f"Error extracting action: {str(e)}")
            return None

    async def get_chat_response(self, user_message, conversation_history):
        """Get response from Gemini API with page context and action handling"""
        try:
            # Extract action request
            action_request = await self._extract_action_request(user_message)
            
            # Handle action if found
            if action_request and action_request['action'] in self.actions:
                action_func = self.actions[action_request['action']]
                action_result = await action_func(**action_request['params'])
                
                # Update last action
                self.last_action = f"{action_request['action']}: {action_request['params']}"
                
                # Add confirmation and next steps
                response = f"{action_result}\n\nIs there anything else you'd like me to help you with?"
                
                return {
                    "message": response,
                    "navigation": None
                }
            
            # Get current page context
            page_context = self._get_page_context()
            
            # Build conversation with page context and clearer action instructions
            conv_str = f"""System: You are an AI assistant for the AttendanceAI system.

Current Context:
{page_context}

Last Action: {self.last_action if self.last_action else 'No recent action'}

Available Actions:
1. Update attendance: "mark student [ID] as [present/absent] [today/date]"
2. Update student: "update student [ID] [name/class/division] to [value]"
3. Update teacher: "update teacher [ID] [name/subjects] to [value]"

Your role is to help with the current page and context. For administrative actions, please use the exact formats above.
"""
            
            # Add recent conversation history (limit to last 5 messages)
            recent_history = conversation_history[-5:] if conversation_history else []
            for msg in recent_history:
                role = "User" if msg["role"] == "user" else "Assistant"
                conv_str += f"{role}: {msg['content']}\n"
            
            # Add current message
            conv_str += f"User: {user_message}\n"
            
            # Call Gemini API
            response = self.model.generate_content(conv_str)
            
            if not response.text:
                return {
                    "message": "I'm having trouble understanding. Could you please rephrase your request using one of the formats shown above?",
                    "navigation": None
                }
            
            # Process response
            message_content = self._enhance_response(response.text.strip())
            
            return {
                "message": message_content,
                "navigation": self._extract_navigation_command(message_content)
            }
            
        except Exception as e:
            current_app.logger.error(f"Gemini API error: {str(e)}")
            return {
                "message": "I'm having technical difficulties. Please try again.",
                "navigation": None
            }

    def _enhance_response(self, message):
        """Enhance response with page-specific context"""
        # Keep responses focused
        if len(message) > 500:
            message = message[:500] + "..."

        # Add page-specific navigation suggestions
        if self.current_page == 'dashboard':
            if 'attendance' in message.lower() and '#show-attendance' not in message:
                message += "\n\nUse #show-attendance to view detailed attendance records."
            elif 'recognition' in message.lower() and '#show-recognize' not in message:
                message += "\n\nUse #show-recognize to start face recognition."
        elif self.current_page == 'attendance/view':
            if 'recognition' in message.lower():
                message += "\n\nUse #show-recognize to mark new attendance."
        elif self.current_page == 'recognition/classroom':
            if 'attendance' in message.lower():
                message += "\n\nUse #show-attendance to view marked attendance."
        
        return message

    def _extract_navigation_command(self, message):
        """Extract navigation command from message"""
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

    async def get_system_message(self, event_type, context=None):
        """Generate natural, context-aware system event responses"""
        try:
            # Update last action
            self.last_action = f"{event_type}: {context if context else ''}"
            
            # Create context-aware event prompt
            event_prompt = f"""Generate a natural, friendly response for this event in the attendance system:
            Current Page: {self.current_page}
            Event: {event_type}
            Context: {context if context else 'No additional context'}
            Last Action: {self.last_action}
            
            Guidelines:
            - Be friendly and conversational
            - Keep it brief but helpful
            - Add relevant suggestions when appropriate
            - Use emojis sparingly for emphasis
            - Match the tone to the event (success = enthusiastic, error = empathetic)"""
            
            response = self.model.generate_content(event_prompt)
            
            if not response.text:
                return self._get_fallback_message(event_type)
            
            return response.text.strip()
            
        except Exception as e:
            current_app.logger.error(f"Error generating system message: {str(e)}")
            return self._get_fallback_message(event_type)

    def _get_fallback_message(self, event_type):
        """Get natural, context-aware fallback messages"""
        if self.current_page == 'recognition/classroom':
            fallback_messages = {
                'camera_start': "Great! I can see you now. Make sure your face is clearly visible in the frame 📸",
                'camera_stop': "Camera turned off. Let me know when you want to start face recognition again!",
                'faces_detected': "I see you! Just checking the attendance records... 👀",
                'no_faces': "Hmm, I can't see anyone right now. Could you adjust your position or check the lighting?",
                'attendance_marked': "Got it! I've marked your attendance. Have a great class! ✅",
                'attendance_error': "Oops, something went wrong with marking attendance. Let's try that again, shall we?"
            }
        elif self.current_page == 'attendance/view':
            fallback_messages = {
                'attendance_marked': "Perfect! The attendance record has been updated ✨",
                'attendance_error': "Sorry about that! The update didn't go through. Want to try again?",
                'record_updated': "Changes saved successfully! Everything's up to date now 👍",
                'filter_applied': "I've filtered the records just how you wanted them",
                'loading_records': "Just a moment while I fetch those attendance records for you..."
            }
        elif self.current_page == 'admin/manage/students':
            fallback_messages = {
                'student_updated': "Student details have been updated successfully! ✨",
                'student_added': "Great! The new student has been added to the system 🎉",
                'student_deleted': "Student record has been removed from the system",
                'update_error': "Hmm, couldn't update that right now. Want to try again?"
            }
        elif self.current_page == 'admin/manage/teachers':
            fallback_messages = {
                'teacher_updated': "Teacher information updated successfully! ✨",
                'teacher_added': "Excellent! New teacher has been added to the system 🎉",
                'teacher_deleted': "Teacher record has been removed from the system",
                'update_error': "Sorry, couldn't update that right now. Shall we try again?"
            }
        else:
            fallback_messages = {
                'processing': "Working on it... Just give me a moment! ⚡",
                'error': "Oops! That didn't work as expected. Want to try again?",
                'success': "All done! Everything worked perfectly ✨",
                'saving': "Just saving those changes for you...",
                'loading': "Let me fetch that information for you..."
            }
            
        return fallback_messages.get(event_type, "Done! What would you like to do next?") 