from flask import Blueprint, jsonify, request, current_app, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.utils.decorators import role_required
from datetime import datetime, timedelta
import base64
import io
from PIL import Image, ImageEnhance
import cv2
import numpy as np
import logging
import boto3
import os
import time
from app.services.rekognition_service import RekognitionService
from flask_wtf.csrf import generate_csrf

recognition_bp = Blueprint('recognition', __name__)

# AWS Configuration
rekognition_client = boto3.client(
    'rekognition',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)

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

@recognition_bp.route('/register', methods=['GET'])
@login_required
@role_required(['admin', 'teacher'])
def register():
    """Face registration page"""
    assigned_classes = []
    if current_user.role == 'teacher':
        assigned_classes = current_user.classes
    elif current_user.role == 'admin':
        # For admin, create a list of all possible class-division combinations
        for class_num in range(1, 13):
            for division in ['A', 'B', 'C', 'D']:
                assigned_classes.append(f"{class_num}-{division}")
    return render_template('recognition/register.html', assigned_classes=assigned_classes)

@recognition_bp.route('/register', methods=['POST'])
@login_required
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

        # For teachers, validate that they can register students for this class
        if current_user.role == 'teacher':
            class_division = f"{student_class}-{student_division}"
            if class_division not in current_user.classes:
                return jsonify({"error": "You are not authorized to register students for this class"}), 403

        # Clean name for external ID
        sanitized_name = "".join(c if c.isalnum() or c in "_-." else "_" for c in name)
        external_image_id = f"{sanitized_name}_{student_id}"
        
        current_app.logger.info(f"Processing registration for external_image_id: {external_image_id}")
        
        # Process image
        try:
            image_data = image.split(",")[1] if "," in image else image
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
            
        # Check if face already exists in the collection
        try:
            rekognition_service = RekognitionService()
            faces = rekognition_service.detect_faces(enhanced_image_bytes)
            if not faces:
                return jsonify({"error": "No face detected in the image. Please try with a clearer photo"}), 400
                
            # Search for similar faces
            face = faces[0]
            match = rekognition_service.search_face(face, enhanced_image_bytes)
            if match:
                # Get the matched student's details
                matched_student_ref = current_app.db.collection('users').where('student_id', '==', match['student_id']).limit(1).get()
                if matched_student_ref:
                    matched_student = matched_student_ref[0].to_dict()
                    return jsonify({
                        "error": f"This face is already registered for student {matched_student.get('name')} (ID: {matched_student.get('student_id')}) in class {matched_student.get('class')}-{matched_student.get('division')}"
                    }), 400
                else:
                    return jsonify({"error": "This face is already registered in the system"}), 400
        except Exception as e:
            current_app.logger.error(f"Error checking for existing face: {str(e)}")
            return jsonify({"error": "Failed to check for existing face. Please try again"}), 500
        
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

@recognition_bp.route('/recognize', methods=['POST'])
@login_required
@role_required(['admin', 'teacher'])
def recognize():
    """Recognize faces in an image and mark attendance"""
    try:
        data = request.json
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'error': 'No image data provided'}), 400
            
        # Clean base64 image data
        if 'base64,' in image_data:
            image_data = image_data.split('base64,')[1]
            
        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        
        # Enhance image before detection
        pil_image = Image.open(io.BytesIO(image_bytes))
        enhanced_image = enhance_image(pil_image)
        buffered = io.BytesIO()
        enhanced_image.save(buffered, format="JPEG")
        enhanced_image_bytes = buffered.getvalue()
        
        # Use AWS Rekognition to detect faces
        rekognition_service = RekognitionService()
        faces = rekognition_service.detect_faces(enhanced_image_bytes)
        
        if not faces:
            return jsonify({
                'message': 'No faces detected in the image',
                'total_faces': 0,
                'identified_people': []
            })
            
        # Get teacher's assigned classes
        teacher_classes = []
        if current_user.role == 'teacher':
            teacher_classes = getattr(current_user, 'classes', [])
            if not teacher_classes:
                return jsonify({
                    'error': 'No classes assigned to your account'
                }), 403
            
        # Search for each face in the collection
        identified_people = []
        for face in faces:
            try:
                match = rekognition_service.search_face(face, enhanced_image_bytes)
                if match:
                    student_id = match['student_id']
                    confidence = match['confidence']
                    
                    # Get student details
                    student_ref = current_app.db.collection('users').where('student_id', '==', student_id).limit(1).get()
                    if not student_ref:
                        identified_people.append({
                            'message': f'Student {student_id} not found in database'
                        })
                        continue

                    student_doc = student_ref[0]
                    student_data = student_doc.to_dict()
                    student_class = f"{student_data.get('class')}-{student_data.get('division')}"
                    student_name = student_data.get('name', '')
                    
                    # For teachers, check if they can mark attendance for this student
                    if current_user.role == 'teacher' and student_class not in teacher_classes:
                        identified_people.append({
                            'student_id': student_id,
                            'name': student_name,
                            'class': student_data.get('class', ''),
                            'division': student_data.get('division', ''),
                            'message': f'Not authorized to mark attendance for student in class {student_class}'
                        })
                        continue
                    
                    # Mark attendance
                    attendance_data = {
                        'student_id': student_id,
                        'student_name': student_name,
                        'name': student_name,
                        'class': student_data.get('class', ''),
                        'division': student_data.get('division', ''),
                        'class_id': student_class,  # Add class_id for filtering
                        'status': 'PRESENT',
                        'date': datetime.now().strftime('%Y-%m-%d'),
                        'timestamp': datetime.now().isoformat(),
                        'marked_by': current_user.email,
                        'confidence': confidence
                    }
                    
                    # Check if attendance already exists for today
                    today = datetime.now().strftime('%Y-%m-%d')
                    existing_attendance = current_app.db.collection('attendance').where(
                        'student_id', '==', student_id
                    ).where('date', '==', today).get()
                    
                    if existing_attendance:
                        # Update existing attendance
                        doc = existing_attendance[0]
                        doc.reference.update({
                            'status': 'PRESENT',
                            'timestamp': datetime.now().isoformat(),
                            'marked_by': current_user.email,
                            'confidence': confidence
                        })
                        current_app.logger.info(f"Updated attendance for student {student_id}")
                    else:
                        # Add new attendance record
                        doc_ref = current_app.db.collection('attendance').add(attendance_data)
                        current_app.logger.info(f"Created new attendance record for student {student_id}")
                    
                    identified_people.append({
                        'student_id': student_id,
                        'name': student_name,
                        'class': student_data.get('class', ''),
                        'division': student_data.get('division', ''),
                        'confidence': confidence,
                        'message': 'Attendance marked successfully'
                    })
                else:
                    identified_people.append({
                        'message': 'No match found for this face'
                    })
            except Exception as e:
                current_app.logger.error(f"Error processing face: {str(e)}")
                identified_people.append({
                    'message': f'Error processing face: {str(e)}'
                })
                
        return jsonify({
            'message': 'Recognition complete',
            'total_faces': len(faces),
            'identified_people': identified_people
        })
        
    except Exception as e:
        current_app.logger.error(f"Recognition error: {str(e)}")
        return jsonify({'error': str(e)}), 500 

@recognition_bp.route('/take_attendance')
@login_required
def take_attendance():
    """Take attendance using face recognition"""
    if current_user.role != 'student':
        flash('Only students can use this feature', 'error')
        return redirect(url_for('main.dashboard'))
        
    return render_template('recognition/take_attendance.html') 

@recognition_bp.route('/verify_attendance', methods=['POST'])
@login_required
def verify_attendance():
    """Verify student attendance using face recognition"""
    if current_user.role != 'student':
        return jsonify({'error': 'Only students can use this feature'}), 403
        
    try:
        # Get photo from the request
        photo_data = request.form.get('photo')
        if not photo_data:
            return jsonify({'error': 'No photo provided'}), 400
            
        # Clean base64 image data
        if 'base64,' in photo_data:
            photo_data = photo_data.split('base64,')[1]
            
        # Decode base64 image
        photo_bytes = base64.b64decode(photo_data)
        
        # Initialize Rekognition service
        rekognition_service = RekognitionService()
        
        # Detect faces
        faces = rekognition_service.detect_faces(photo_bytes)
        if not faces:
            return jsonify({'error': 'No face detected in the photo. Please try again with a clearer photo'}), 400
            
        # We only expect one face in the photo
        face = faces[0]
        match = rekognition_service.search_face(face, photo_bytes)
        
        if not match:
            return jsonify({'error': 'Face not recognized. Please try again'}), 400
            
        # Verify that the matched student is the current user
        student_id = match['student_id']
        student_ref = current_app.db.collection('users').where('student_id', '==', student_id).limit(1).get()
        
        if not student_ref:
            return jsonify({'error': 'Student not found in database'}), 404
            
        student_doc = student_ref[0]
        student_data = student_doc.to_dict()
        
        if student_data.get('email') != current_user.email:
            return jsonify({'error': 'Face match does not correspond to logged in user'}), 403
            
        # Mark attendance
        attendance_data = {
            'student_id': student_id,
            'student_name': student_data.get('name', ''),
            'class': student_data.get('class', ''),
            'division': student_data.get('division', ''),
            'class_id': f"{student_data.get('class')}-{student_data.get('division')}",
            'status': 'PRESENT',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'timestamp': datetime.now().isoformat(),
            'marked_by': 'self',
            'confidence': match['confidence']
        }
        
        # Check if attendance already exists for today
        today = datetime.now().strftime('%Y-%m-%d')
        existing_attendance = current_app.db.collection('attendance').where(
            'student_id', '==', student_id
        ).where('date', '==', today).get()
        
        if existing_attendance:
            # Update existing attendance
            doc = existing_attendance[0]
            doc.reference.update({
                'status': 'PRESENT',
                'timestamp': datetime.now().isoformat(),
                'marked_by': 'self',
                'confidence': match['confidence']
            })
            current_app.logger.info(f"Updated attendance for student {student_id}")
        else:
            # Add new attendance record
            doc_ref = current_app.db.collection('attendance').add(attendance_data)
            current_app.logger.info(f"Created new attendance record for student {student_id}")
            
        return jsonify({
            'message': 'Attendance marked successfully',
            'data': {
                'confidence': match['confidence']
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error verifying attendance: {str(e)}")
        return jsonify({'error': str(e)}), 500 

@recognition_bp.route('/classroom')
@login_required
@role_required(['admin', 'teacher'])
def classroom_mode():
    """Classroom mode for real-time attendance tracking"""
    return render_template('recognition/classroom_mode.html')

@recognition_bp.route('/detect_faces', methods=['POST'])
def detect_faces():
    """Detect faces in an image and return matches."""
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'No image data provided'}), 400

        # Remove data URL prefix if present
        image_data = data['image']
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]

        # Decode base64 image
        image_bytes = base64.b64decode(image_data)
        
        # Enhance image before detection
        pil_image = Image.open(io.BytesIO(image_bytes))
        enhanced_image = enhance_image(pil_image)
        buffered = io.BytesIO()
        enhanced_image.save(buffered, format="JPEG")
        enhanced_image_bytes = buffered.getvalue()
        
        # Initialize Rekognition service
        rekognition_service = RekognitionService()
        
        # Detect faces using the service
        faces = rekognition_service.detect_faces(enhanced_image_bytes)
        if not faces:
            return jsonify({'faces': []})

        # Get today's date at midnight for attendance check
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Process each face
        processed_faces = []
        unique_students = set()  # Track unique students
        
        for face in faces:
            # Get bounding box - handle both possible response structures
            bbox = face.get('BoundingBox', face.get('boundingBox', {}))
            face_data = {
                'boundingBox': {
                    'x': int(bbox.get('Left', bbox.get('x', 0)) * 1280),
                    'y': int(bbox.get('Top', bbox.get('y', 0)) * 720),
                    'width': int(bbox.get('Width', bbox.get('width', 0)) * 1280),
                    'height': int(bbox.get('Height', bbox.get('height', 0)) * 720)
                },
                'match': None
            }
            
            # Search for this specific face
            match = rekognition_service.search_face(face, enhanced_image_bytes)
            if match:
                student_id = match['student_id']
                # Only process if we haven't seen this student yet
                if student_id not in unique_students:
                    unique_students.add(student_id)
                    
                    # Get student details
                    student_ref = current_app.db.collection('users').where('student_id', '==', student_id).limit(1).get()
                    if len(list(student_ref)) > 0:
                        student = student_ref[0].to_dict()
                        # Check if attendance is already marked
                        attendance_ref = current_app.db.collection('attendance').where('student_id', '==', student_id).where('date', '>=', today).limit(1).get()
                        already_marked = len(list(attendance_ref)) > 0
                        
                        face_data['match'] = {
                            'student_id': student_id,
                            'name': student.get('name', ''),
                            'confidence': match['confidence'],
                            'alreadyMarked': already_marked
                        }
            
            processed_faces.append(face_data)

        return jsonify({'faces': processed_faces, 'uniqueCount': len(unique_students)})

    except Exception as e:
        current_app.logger.error(f"Error in detect_faces: {str(e)}")
        return jsonify({'error': str(e)}), 500

def mark_all_absent(date_str=None):
    """Mark all students as absent for a given date."""
    try:
        # Get current timestamp if date not provided
        now = datetime.now()
        date_str = date_str or now.strftime('%Y-%m-%d')
        
        # Get all students in the system
        all_students = current_app.db.collection('users').where('role', '==', 'student').get()
        
        for student_doc in all_students:
            student_data = student_doc.to_dict()
            student_id = student_data.get('student_id')
            
            if not student_id:
                continue
                
            attendance_data = {
                'student_id': student_id,
                'student_name': student_data.get('name', ''),
                'class': student_data.get('class', ''),
                'division': student_data.get('division', ''),
                'class_id': f"{student_data.get('class')}-{student_data.get('division')}",
                'status': 'ABSENT',
                'date': date_str,
                'timestamp': now.isoformat(),
                'marked_by': 'system',
                'method': 'auto'
            }
            
            # Check if attendance already exists for the date
            existing_attendance = current_app.db.collection('attendance').where(
                'student_id', '==', student_id
            ).where('date', '==', date_str).get()
            
            if not existing_attendance:  # Only create if no record exists
                current_app.db.collection('attendance').add(attendance_data)

        return True
    except Exception as e:
        current_app.logger.error(f"Error marking all absent: {str(e)}")
        return False

@recognition_bp.route('/mark_classroom_attendance', methods=['POST'])
def mark_classroom_attendance():
    """Mark attendance for multiple students detected in classroom mode."""
    try:
        data = request.get_json()
        if not data or 'students' not in data:
            return jsonify({'error': 'No student data provided'}), 400

        students = data['students']
        if not students:
            return jsonify({'error': 'No students to mark attendance for'}), 400

        # Get current timestamp
        now = datetime.now()
        today_str = now.strftime('%Y-%m-%d')

        # Ensure all students have an absent record for today
        mark_all_absent(today_str)

        # Update detected students as present
        marked_count = 0
        for student in students:
            student_id = student.get('student_id')
            if not student_id:
                continue

            # Get attendance record for today
            existing_attendance = current_app.db.collection('attendance').where(
                'student_id', '==', student_id
            ).where('date', '==', today_str).get()
            
            if existing_attendance:
                # Update to present
                doc = existing_attendance[0]
                doc.reference.update({
                    'status': 'PRESENT',
                    'timestamp': now.isoformat(),
                    'marked_by': current_user.email,
                    'confidence': student.get('confidence', 0),
                    'method': 'classroom'
                })
                marked_count += 1

        return jsonify({
            'message': f'Successfully marked {marked_count} students as present',
            'marked_count': marked_count
        })

    except Exception as e:
        current_app.logger.error(f"Error in mark_classroom_attendance: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Add this route to manually trigger marking all absent (for testing or manual runs)
@recognition_bp.route('/mark_all_absent', methods=['POST'])
@login_required
@role_required(['admin'])
def mark_all_absent_route():
    """Admin route to manually mark all students as absent for a date."""
    try:
        data = request.get_json()
        date_str = data.get('date') if data else None
        
        if mark_all_absent(date_str):
            return jsonify({'message': 'Successfully marked all students as absent'})
        else:
            return jsonify({'error': 'Failed to mark students as absent'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500 