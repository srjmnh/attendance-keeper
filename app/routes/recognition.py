from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from app.utils.decorators import role_required
from datetime import datetime, timedelta
import base64
import io
from PIL import Image, ImageEnhance
import cv2
import numpy as np
import logging

bp = Blueprint('recognition', __name__)

COLLECTION_ID = "students"  # Hardcode the collection ID to match the example code

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
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        student_id = data.get('student_id', '').strip()
        student_class = data.get('class')
        student_division = data.get('division', '').strip()
        image = data.get('image', '')
        
        # Validate required fields
        validation_errors = []
        if not name:
            validation_errors.append("Name is required")
        if not student_id:
            validation_errors.append("Student ID is required")
        if not student_class:
            validation_errors.append("Class is required")
        if not student_division:
            validation_errors.append("Division is required")
        if not image:
            validation_errors.append("Image is required")
            
        if validation_errors:
            return jsonify({"error": "; ".join(validation_errors)}), 400

        # Validate data formats
        try:
            student_class = int(student_class)
            if not (1 <= student_class <= 12):
                return jsonify({"error": "Class must be between 1 and 12"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid class format. Must be a number between 1 and 12"}), 400
            
        if student_division not in ['A', 'B', 'C', 'D']:
            return jsonify({"error": "Division must be A, B, C, or D"}), 400

        # Clean name for external ID
        sanitized_name = "".join(c if c.isalnum() or c in "_-." else "_" for c in name)
        external_image_id = f"{sanitized_name}_{student_id}"
        
        current_app.logger.info(f"Processing registration for external_image_id: {external_image_id}")
        
        # Process image
        try:
            image_data = image.split(",")[1]
            image_bytes = base64.b64decode(image_data)
            
            # Enhance image before indexing
            pil_image = Image.open(io.BytesIO(image_bytes))
            enhanced_image = enhance_image(pil_image)
            buffered = io.BytesIO()
            enhanced_image.save(buffered, format="JPEG")
            enhanced_image_bytes = buffered.getvalue()
            
            current_app.logger.info("Image processed successfully")
        except Exception as e:
            current_app.logger.error(f"Error processing image: {str(e)}")
            return jsonify({"error": "Failed to process image. Please try with a different image"}), 400
        
        # Check if student already exists
        existing_student = current_app.db.collection('users').where('student_id', '==', student_id).get()
        if len(list(existing_student)) > 0:
            return jsonify({"error": "Student ID already exists"}), 400
        
        # Index face in AWS Rekognition
        try:
            response = current_app.rekognition.index_faces(
                CollectionId=COLLECTION_ID,
                Image={'Bytes': enhanced_image_bytes},
                ExternalImageId=external_image_id,
                DetectionAttributes=['ALL'],
                QualityFilter='AUTO'
            )
            
            if not response.get('FaceRecords'):
                return jsonify({"error": "No face detected in the image. Please try with a clearer photo"}), 400

            current_app.logger.info(f"Indexed face with external ID: {external_image_id}")
            current_app.logger.info(f"AWS Response: {response}")

        except Exception as e:
            current_app.logger.error(f"AWS Rekognition error: {str(e)}")
            return jsonify({"error": "Failed to process face. Please try with a different image"}), 500

        # Save student data to Firestore
        student_data = {
            'name': name,
            'student_id': student_id,
            'class': student_class,
            'division': student_division.upper(),
            'role': 'student',
            'created_at': datetime.utcnow().isoformat(),
            'face_id': external_image_id,  # This must match the ExternalImageId used in AWS
            'rekognition_face_id': response['FaceRecords'][0]['Face']['FaceId']
        }

        # Add student to Firestore
        try:
            current_app.logger.info(f"Saving student data: {student_data}")
            doc_ref = current_app.db.collection('users').add(student_data)
            current_app.logger.info(f"Student data saved with document ID: {doc_ref[1].id}")
        except Exception as e:
            current_app.logger.error(f"Firestore error: {str(e)}")
            # If Firestore save fails, delete the face from Rekognition
            try:
                current_app.rekognition.delete_faces(
                    CollectionId=COLLECTION_ID,
                    FaceIds=[response['FaceRecords'][0]['Face']['FaceId']]
                )
            except:
                pass
            return jsonify({"error": "Failed to save student data. Please try again"}), 500

        return jsonify({
            "message": f"Student {name} with ID {student_id} registered successfully!",
            "data": {
                "name": name,
                "student_id": student_id,
                "class": student_class,
                "division": student_division,
                "face_id": external_image_id
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error registering face: {str(e)}")
        return jsonify({"error": "An unexpected error occurred. Please try again"}), 500

@bp.route('/recognize', methods=['POST'])
@login_required
def recognize_face():
    """Recognize faces in an image"""
    data = request.get_json()
    image_str = data.get('image')
    
    if not image_str:
        return jsonify({"error": "No image provided"}), 400

    try:
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
        detect_response = current_app.rekognition.client.detect_faces(
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
            try:
                # Get the bounding box for this face
                bbox = face.get('BoundingBox')
                if not bbox:
                    current_app.logger.error(f"No bounding box found for face {idx+1}")
                    continue

                # Crop the face using the bounding box
                image = Image.open(io.BytesIO(enhanced_image_bytes))
                width, height = image.size
                left = int(bbox['Left'] * width)
                top = int(bbox['Top'] * height)
                right = int((bbox['Left'] + bbox['Width']) * width)
                bottom = int((bbox['Top'] + bbox['Height']) * height)

                # Add padding
                padding = int(min(width, height) * 0.1)
                left = max(0, left - padding)
                top = max(0, top - padding)
                right = min(width, right + padding)
                bottom = min(height, bottom + padding)

                face_image = image.crop((left, top, right, bottom))
                
                # Convert cropped face to bytes
                buffered = io.BytesIO()
                face_image.save(buffered, format="JPEG")
                face_bytes = buffered.getvalue()

                try:
                    # Search for the cropped face
                    response = current_app.rekognition.client.search_faces_by_image(
                        CollectionId=COLLECTION_ID,
                        Image={'Bytes': face_bytes},
                        MaxFaces=1,
                        FaceMatchThreshold=80
                    )
                    
                    matches = response.get('FaceMatches', [])
                    current_app.logger.info(f"Search response for face {idx+1}: {response}")
                    
                except Exception as e:
                    current_app.logger.error(f"Error searching face {idx+1}: {str(e)}")
                    identified_people.append({
                        "message": "Face not recognized",
                        "confidence": "N/A"
                    })
                    continue

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

                current_app.logger.info(f"Found match with external ID: {ext_id} and confidence: {confidence}")

                # Get student details from Firestore
                student_query = current_app.db.collection('users').where('face_id', '==', ext_id).limit(1).get()
                student_docs = list(student_query)
                current_app.logger.info(f"Found {len(student_docs)} student documents for face_id {ext_id}")
                
                if not student_docs:
                    # Try searching by student ID (in case face_id field is missing)
                    student_id = ext_id.split('_')[-1]  # Get student ID from external_image_id
                    current_app.logger.info(f"Trying fallback search with student_id: {student_id}")
                    student_query = current_app.db.collection('users').where('student_id', '==', student_id).limit(1).get()
                    student_docs = list(student_query)
                    current_app.logger.info(f"Fallback: Found {len(student_docs)} student documents for student_id {student_id}")

                if not student_docs:
                    current_app.logger.error(f"No student found for face_id {ext_id} or student_id {student_id}")
                    identified_people.append({
                        "message": "Student data not found",
                        "confidence": confidence
                    })
                    continue

                student_doc = student_docs[0]
                student_data = student_doc.to_dict()
                current_app.logger.info(f"Student data: {student_data}")

                # Update face_id if it's missing
                if 'face_id' not in student_data:
                    current_app.logger.info(f"Updating missing face_id for student {student_doc.id} to {ext_id}")
                    current_app.db.collection('users').document(student_doc.id).update({
                        'face_id': ext_id
                    })
                    current_app.logger.info(f"Updated missing face_id for student {student_doc.id}")

                student_name = student_data.get('name', 'Unknown')
                student_id = student_data.get('student_id', 'Unknown')
                student_class = student_data.get('class', '')
                student_division = student_data.get('division', '')

                identified_people.append({
                    "name": student_name,
                    "student_id": student_id,
                    "confidence": confidence,
                    "class": student_class,
                    "division": student_division
                })

                # Check if attendance already exists for today
                today = datetime.utcnow().date()
                try:
                    attendance_query = current_app.db.collection("attendance")\
                        .where('student_id', '==', student_id)\
                        .where('timestamp', '>=', today.isoformat())\
                        .where('timestamp', '<', (today + timedelta(days=1)).isoformat())\
                        .limit(1)\
                        .get()

                    if not list(attendance_query):
                        # Log attendance only if not already marked today
                        attendance_doc = {
                            "student_id": student_id,
                            "name": student_name,
                            "class": student_class,
                            "division": student_division,
                            "timestamp": datetime.utcnow().isoformat(),
                            "status": "PRESENT"
                        }
                        current_app.db.collection("attendance").add(attendance_doc)
                        current_app.logger.info(f"Added attendance record for student {student_id}")
                    else:
                        current_app.logger.info(f"Student {student_id} already has attendance for today")
                except Exception as e:
                    current_app.logger.error(f"Error checking/adding attendance: {str(e)}")
                    if "The query requires an index" in str(e):
                        current_app.logger.error("Missing Firestore index. Please create the required index.")
                    # Continue without marking attendance
                    pass

            except Exception as e:
                current_app.logger.error(f"Error processing face {idx+1}: {str(e)}")
                identified_people.append({
                    "message": f"Error processing face {idx+1}: {str(e)}",
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