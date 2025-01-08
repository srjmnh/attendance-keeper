from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.services.gemini_service import GeminiService
from app.services.db_service import DatabaseService

bp = Blueprint('ai', __name__)
gemini = GeminiService()
db = DatabaseService()

@bp.route('/api/ai/analyze-attendance', methods=['POST'])
@login_required
def analyze_attendance():
    """Analyze attendance data using AI"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        
        # Get attendance data
        attendance_data = db.get_student_attendance(student_id)
        if not attendance_data:
            return jsonify({"error": "No attendance data found"}), 404
        
        # Get AI analysis
        analysis = gemini.analyze_attendance(attendance_data)
        return jsonify({"analysis": analysis})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/api/ai/get-recommendations', methods=['POST'])
@login_required
def get_recommendations():
    """Get AI recommendations for a student"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        
        # Get student data
        student_data = db.get_student_data(student_id)
        if not student_data:
            return jsonify({"error": "Student not found"}), 404
        
        # Get AI recommendations
        recommendations = gemini.get_student_recommendations(student_data)
        return jsonify({"recommendations": recommendations})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/api/ai/chat', methods=['POST'])
@login_required
def chat():
    """Chat with AI assistant"""
    try:
        data = request.get_json()
        message = data.get('message') or data.get('prompt')
        context = data.get('context')  # Optional context
        
        if not message:
            return jsonify({"error": "Message is required"}), 400
        
        # Get AI response
        response = gemini.chat_with_assistant(message, context)
        return jsonify({"message": response})
    except Exception as e:
        current_app.logger.error(f"Error in chat: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/api/ai/generate-report', methods=['POST'])
@login_required
def generate_report():
    """Generate AI report summary"""
    try:
        data = request.get_json()
        report_data = data.get('report_data')
        
        if not report_data:
            return jsonify({"error": "Report data is required"}), 400
        
        # Get AI summary
        summary = gemini.generate_report_summary(report_data)
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500 