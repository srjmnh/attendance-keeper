from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from ..services.face_service import FaceService
from ..services.image_service import ImageService
from ..services.ai_service import AIService
from ..models.attendance import Attendance
from functools import wraps
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('recognition', __name__)

def init_services():
    """Initialize services with current app config"""
    face_service = FaceService(
        aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
        aws_region=current_app.config['AWS_REGION'],
        collection_id=current_app.config['COLLECTION_ID']
    )
    ai_service = AIService(api_key=current_app.config['GEMINI_API_KEY'])
    return face_service, ai_service

def teacher_required(f):
    """Decorator to require teacher or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or (
            not current_user.is_teacher and not current_user.is_admin
        ):
            return jsonify({'error': 'Teacher or admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/register', methods=['POST'])
@login_required
@teacher_required
def register_face():
    """Register a student's face"""
    try:
        data = request.get_json()
        if not data or 'image' not in data or 'name' not in data or 'student_id' not in data:
            return jsonify({'error': 'Missing required fields'}), 400

        face_service, ai_service = init_services()

        # Analyze image quality first
        image = ImageService.process_base64_image(data['image'])
        quality_analysis = ai_service.analyze_image_quality(image)
        
        if 'error' in quality_analysis:
            return jsonify({'error': 'Image quality analysis failed', 
                          'details': quality_analysis['error']}), 400

        # Register face if quality is acceptable
        external_image_id = f"{data['name']}_{data['student_id']}"
        face_id = face_service.register_face(data['image'], external_image_id)

        return jsonify({
            'message': 'Face registered successfully',
            'face_id': face_id,
            'quality_analysis': quality_analysis
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error registering face: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/recognize', methods=['POST'])
@login_required
def recognize_faces():
    """Recognize faces in an image and mark attendance"""
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'No image provided'}), 400

        face_service, ai_service = init_services()

        # Optional subject information
        subject_id = data.get('subject_id')
        subject_name = data.get('subject_name')

        # Recognize faces
        recognition_results = face_service.recognize_faces(
            data['image'],
            min_confidence=current_app.config['FACE_MATCH_THRESHOLD']
        )

        # Analyze recognition results
        analysis = ai_service.analyze_recognition_results(recognition_results)

        # Mark attendance for recognized faces
        if recognition_results['identified_people']:
            Attendance.mark_attendance_from_recognition(
                recognition_results,
                subject_id=subject_id,
                subject_name=subject_name,
                verified_by=current_user.id if current_user.is_teacher or current_user.is_admin else None
            )

        return jsonify({
            'recognition_results': recognition_results,
            'analysis': analysis,
            'message': f"Processed {recognition_results['total_faces']} faces"
        }), 200

    except Exception as e:
        logger.error(f"Error in face recognition: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/faces/<face_id>', methods=['DELETE'])
@login_required
@teacher_required
def delete_face(face_id):
    """Delete a registered face"""
    try:
        face_service, _ = init_services()
        face_service.delete_face(face_id)
        return jsonify({'message': 'Face deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting face: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@bp.route('/faces', methods=['GET'])
@login_required
@teacher_required
def list_faces():
    """List all registered faces"""
    try:
        face_service, _ = init_services()
        faces = face_service.list_faces()
        return jsonify({'faces': faces}), 200
    except Exception as e:
        logger.error(f"Error listing faces: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 