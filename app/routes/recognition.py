from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app.utils.decorators import role_required
from datetime import datetime
import base64
import io
from PIL import Image, ImageEnhance
import cv2
import numpy as np
import logging

bp = Blueprint('recognition', __name__)

def enhance_image(pil_image):
    """
    Enhance image quality to improve face detection in distant group photos.
    This includes increasing brightness and contrast.
    """
    # Convert PIL image to OpenCV format
    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    # Increase brightness and contrast
    alpha = 1.2  # Contrast control (1.0-3.0)
    beta = 30    # Brightness control (0-100)
    enhanced_cv_image = cv2.convertScaleAbs(cv_image, alpha=alpha, beta=beta)

    # Convert back to PIL Image
    enhanced_pil_image = Image.fromarray(cv2.cvtColor(enhanced_cv_image, cv2.COLOR_BGR2RGB))
    return enhanced_pil_image

@bp.route('/register', methods=['POST'])
@role_required(['admin', 'teacher'])
def register_face():
    """Register a new face"""
    data = request.get_json()
    name = data.get('name')
    student_id = data.get('student_id')
    image = data.get('image')
    
    if not name or not student_id or not image:
        return jsonify({"error": "Missing name, student_id, or image"}), 400

    try:
        # Clean name for external ID
        sanitized_name = "".join(c if c.isalnum() or c in "_-." else "_" for c in name)
        image_data = image.split(",")[1]
        image_bytes = base64.b64decode(image_data)

        # Enhance image before indexing
        pil_image = Image.open(io.BytesIO(image_bytes))
        enhanced_image = enhance_image(pil_image)
        buffered = io.BytesIO()
        enhanced_image.save(buffered, format="JPEG")
        enhanced_image_bytes = buffered.getvalue()

        external_image_id = f"{sanitized_name}_{student_id}"
        
        # Index face in AWS Rekognition
        response = current_app.rekognition.index_faces(
            CollectionId=current_app.config['AWS_COLLECTION_ID'],
            Image={'Bytes': enhanced_image_bytes},
            ExternalImageId=external_image_id,
            DetectionAttributes=['ALL'],
            QualityFilter='AUTO'
        )

        if not response.get('FaceRecords'):
            return jsonify({"error": "No face detected in the image"}), 400

        return jsonify({"message": f"Student {name} with ID {student_id} registered successfully!"}), 200
    except Exception as e:
        current_app.logger.error(f"Error registering face: {str(e)}")
        return jsonify({"error": f"Failed to register face: {str(e)}"}), 500

@bp.route('/recognize', methods=['POST'])
@login_required
def recognize_face():
    """Recognize faces in an image"""
    data = request.get_json()
    image_str = data.get('image')
    subject_id = data.get('subject_id', '')
    
    if not image_str:
        return jsonify({"error": "No image provided"}), 400

    try:
        # Get subject name if provided
        subject_name = ""
        if subject_id:
            subject_doc = current_app.db.collection("subjects").document(subject_id).get()
            if subject_doc.exists:
                subject_name = subject_doc.to_dict().get("name", "")
            else:
                subject_name = "Unknown Subject"

        # Process image
        image_data = image_str.split(",")[1]
        image_bytes = base64.b64decode(image_data)

        # Enhance image before detection
        pil_image = Image.open(io.BytesIO(image_bytes))
        enhanced_image = enhance_image(pil_image)
        buffered = io.BytesIO()
        enhanced_image.save(buffered, format="JPEG")
        enhanced_image_bytes = buffered.getvalue()

        # Detect faces
        detect_response = current_app.rekognition.detect_faces(
            Image={'Bytes': enhanced_image_bytes},
            Attributes=['ALL']
        )

        faces = detect_response.get('FaceDetails', [])
        face_count = len(faces)
        identified_people = []

        if face_count == 0:
            return jsonify({
                "message": "No faces detected in the image.",
                "total_faces": face_count,
                "identified_people": identified_people
            }), 200

        # Process each detected face
        for idx, face in enumerate(faces):
            # Get face bounding box
            bbox = face['BoundingBox']
            pil_img = Image.open(io.BytesIO(enhanced_image_bytes))
            img_width, img_height = pil_img.size

            # Calculate face coordinates
            left = int(bbox['Left'] * img_width)
            top = int(bbox['Top'] * img_height)
            width = int(bbox['Width'] * img_width)
            height = int(bbox['Height'] * img_height)
            right = left + width
            bottom = top + height

            # Crop and process face
            cropped_face = pil_img.crop((left, top, right, bottom))
            buffer = io.BytesIO()
            cropped_face.save(buffer, format="JPEG")
            cropped_face_bytes = buffer.getvalue()

            try:
                # Search for face match
                search_response = current_app.rekognition.search_faces_by_image(
                    CollectionId=current_app.config['AWS_COLLECTION_ID'],
                    Image={'Bytes': cropped_face_bytes},
                    MaxFaces=1,
                    FaceMatchThreshold=60
                )

                matches = search_response.get('FaceMatches', [])
                if not matches:
                    identified_people.append({
                        "message": "Face not recognized",
                        "confidence": "N/A"
                    })
                    continue

                # Process match
                match = matches[0]
                ext_id = match['Face']['ExternalImageId']
                confidence = match['Face']['Confidence']

                # Extract name and ID
                parts = ext_id.split("_", 1)
                if len(parts) == 2:
                    rec_name, rec_id = parts
                else:
                    rec_name, rec_id = ext_id, "Unknown"

                identified_people.append({
                    "name": rec_name,
                    "student_id": rec_id,
                    "confidence": confidence
                })

                # Log attendance if recognized
                if rec_id != "Unknown":
                    attendance_doc = {
                        "student_id": rec_id,
                        "name": rec_name,
                        "timestamp": datetime.utcnow().isoformat(),
                        "subject_id": subject_id,
                        "subject_name": subject_name,
                        "status": "PRESENT"
                    }
                    current_app.db.collection("attendance").add(attendance_doc)

            except Exception as e:
                identified_people.append({
                    "message": f"Error searching face {idx+1}: {str(e)}",
                    "confidence": "N/A"
                })
                continue

        return jsonify({
            "message": f"{face_count} face(s) detected in the photo.",
            "total_faces": face_count,
            "identified_people": identified_people
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error recognizing faces: {str(e)}")
        return jsonify({"error": f"Failed to recognize faces: {str(e)}"}), 500 