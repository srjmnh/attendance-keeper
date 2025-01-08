from flask import render_template, request, jsonify, current_app, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from . import main_bp
from app.services.rekognition_service import RekognitionService
from app.services.chatbot_service import ChatbotService
from app.utils.decorators import role_required

@main_bp.route('/')
@login_required
def dashboard():
    """Main dashboard route that handles all user roles"""
    try:
        # Get subjects based on user role
        subjects = []
        if current_user.role != 'student':
            subjects = current_app.db.collection('subjects').stream()
            subjects = [{'id': doc.id, **doc.to_dict()} for doc in subjects]
        
        # Get recent activities
        activities = []
        if current_user.role == 'admin':
            activities = current_app.db.collection('attendance').order_by('timestamp', direction='DESCENDING').limit(5).stream()
        elif current_user.role == 'teacher':
            activities = current_app.db.collection('attendance').where('subject_id', 'in', current_user.classes).order_by('timestamp', direction='DESCENDING').limit(5).stream()
        else:
            activities = current_app.db.collection('attendance').where('student_id', '==', current_user.id).order_by('timestamp', direction='DESCENDING').limit(5).stream()
        
        activities = [{'id': doc.id, **doc.to_dict()} for doc in activities]
        
        return render_template('dashboard/index.html',
                             subjects=subjects,
                             activities=activities,
                             role=current_user.role)
    except Exception as e:
        current_app.logger.error(f"Error in dashboard route: {str(e)}")
        flash('An error occurred while loading the dashboard.', 'danger')
        return redirect(url_for('auth.login'))

@main_bp.route('/register', methods=['POST'])
@login_required
@role_required(['admin', 'teacher'])
def register_face():
    """Register a face in the AWS Rekognition collection"""
    try:
        data = request.json
        name = data.get('name')
        student_id = data.get('student_id')
        image = data.get('image')
        
        if not all([name, student_id, image]):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Initialize Rekognition service
        rekognition = RekognitionService()
        
        # Decode and process image
        image_bytes = rekognition.decode_base64_image(image)
        external_image_id = f"{name.replace(' ', '_')}_{student_id}"
        
        # Index face
        face_record = rekognition.index_face(image_bytes, external_image_id)
        
        return jsonify({
            "message": f"Successfully registered {name}",
            "face_id": face_record['Face']['FaceId']
        })
    except Exception as e:
        current_app.logger.error(f"Error registering face: {str(e)}")
        return jsonify({"error": str(e)}), 500

@main_bp.route('/recognize', methods=['POST'])
@login_required
def recognize_faces():
    """Recognize faces and mark attendance"""
    try:
        data = request.json
        image = data.get('image')
        subject_id = data.get('subject_id', '')
        
        if not image:
            return jsonify({"error": "No image provided"}), 400
        
        # Get subject details if provided
        subject_name = ""
        if subject_id:
            subject_doc = current_app.db.collection('subjects').document(subject_id).get()
            if subject_doc.exists:
                subject_name = subject_doc.to_dict().get('name', '')
        
        # Initialize Rekognition service
        rekognition = RekognitionService()
        
        # Decode and process image
        image_bytes = rekognition.decode_base64_image(image)
        
        # Detect and search faces
        faces = rekognition.detect_faces(image_bytes)
        identified_people = []
        
        for face in faces:
            # Search for each detected face
            matches = rekognition.search_faces(image_bytes)
            
            if matches:
                match = matches[0]
                ext_id = match['Face']['ExternalImageId']
                confidence = match['Face']['Confidence']
                
                # Parse name and student_id from external_image_id
                name, student_id = ext_id.split('_', 1)
                name = name.replace('_', ' ')
                
                identified_people.append({
                    "name": name,
                    "student_id": student_id,
                    "confidence": round(confidence, 2)
                })
                
                # Log attendance if subject is specified
                if subject_id:
                    current_app.db.collection('attendance').add({
                        "student_id": student_id,
                        "name": name,
                        "subject_id": subject_id,
                        "subject_name": subject_name,
                        "timestamp": datetime.utcnow().isoformat(),
                        "status": "PRESENT"
                    })
            else:
                identified_people.append({
                    "message": "Face not recognized",
                    "confidence": 0
                })
        
        return jsonify({
            "message": f"Processed {len(faces)} faces",
            "identified_people": identified_people
        })
    except Exception as e:
        current_app.logger.error(f"Error recognizing faces: {str(e)}")
        return jsonify({"error": str(e)}), 500

@main_bp.route('/process_prompt', methods=['POST'])
@login_required
def process_chat():
    """Process chat messages using Gemini"""
    try:
        data = request.json
        user_message = data.get('prompt', '').strip()
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        
        # Initialize chatbot
        chatbot = ChatbotService()
        
        # Process message
        response = chatbot.process_message(user_message)
        
        return jsonify({"message": response})
    except Exception as e:
        current_app.logger.error(f"Error processing chat message: {str(e)}")
        return jsonify({"error": str(e)}), 500 