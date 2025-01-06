from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app.services.db_service import DatabaseService
from app.services.face_service import FaceService
from app.services.image_service import ImageService
import base64
from datetime import datetime
import os

recognition = Blueprint('recognition', __name__)
db = DatabaseService()
face_service = FaceService()

# Set up upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
image_service = ImageService(UPLOAD_FOLDER)

@recognition.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    """
    Register student's face for recognition.
    """
    if not current_user.is_student():
        flash('Access denied. Students only.', 'danger')
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        image_data = request.form.get('image')
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'No image provided'
            })
        
        try:
            # Save captured image
            image_data = base64.b64decode(image_data.split(',')[1])
            image_path = image_service.save_image(image_data)
            
            # Detect faces in image
            faces = face_service.detect_faces(image_path)
            if not faces:
                image_service.delete_image(image_path)
                return jsonify({
                    'success': False,
                    'message': 'No face detected in image'
                })
            
            if len(faces) > 1:
                image_service.delete_image(image_path)
                return jsonify({
                    'success': False,
                    'message': 'Multiple faces detected. Please provide a clear photo with only your face'
                })
            
            # Check if face already registered
            if face_service.face_exists(current_user.id):
                image_service.delete_image(image_path)
                return jsonify({
                    'success': False,
                    'message': 'Face already registered'
                })
            
            # Register face
            face_id = face_service.register_face(faces[0], current_user.id)
            if face_id:
                # Update user record with face ID
                db.update_user(current_user.id, {'face_id': face_id})
                
                # Clean up temporary image
                image_service.delete_image(image_path)
                
                return jsonify({
                    'success': True,
                    'message': 'Face registered successfully'
                })
            else:
                image_service.delete_image(image_path)
                return jsonify({
                    'success': False,
                    'message': 'Failed to register face'
                })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            })
    
    return render_template('recognition/register.html')

@recognition.route('/update', methods=['GET', 'POST'])
@login_required
def update():
    """
    Update student's registered face.
    """
    if not current_user.is_student():
        flash('Access denied. Students only.', 'danger')
        return redirect(url_for('main.index'))
    
    if not face_service.face_exists(current_user.id):
        flash('No face registered. Please register your face first.', 'warning')
        return redirect(url_for('recognition.register'))
    
    if request.method == 'POST':
        image_data = request.form.get('image')
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'No image provided'
            })
        
        try:
            # Save captured image
            image_data = base64.b64decode(image_data.split(',')[1])
            image_path = image_service.save_image(image_data)
            
            # Detect faces in image
            faces = face_service.detect_faces(image_path)
            if not faces:
                image_service.delete_image(image_path)
                return jsonify({
                    'success': False,
                    'message': 'No face detected in image'
                })
            
            if len(faces) > 1:
                image_service.delete_image(image_path)
                return jsonify({
                    'success': False,
                    'message': 'Multiple faces detected. Please provide a clear photo with only your face'
                })
            
            # Delete existing face
            face_service.delete_face(current_user.id)
            
            # Register new face
            face_id = face_service.register_face(faces[0], current_user.id)
            if face_id:
                # Update user record with new face ID
                db.update_user(current_user.id, {'face_id': face_id})
                
                # Clean up temporary image
                image_service.delete_image(image_path)
                
                return jsonify({
                    'success': True,
                    'message': 'Face updated successfully'
                })
            else:
                image_service.delete_image(image_path)
                return jsonify({
                    'success': False,
                    'message': 'Failed to update face'
                })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            })
    
    return render_template('recognition/update.html')

@recognition.route('/verify', methods=['POST'])
@login_required
def verify():
    """
    Verify student's face.
    """
    if not current_user.is_student():
        return jsonify({
            'success': False,
            'message': 'Access denied'
        })
    
    image_data = request.form.get('image')
    if not image_data:
        return jsonify({
            'success': False,
            'message': 'No image provided'
        })
    
    try:
        # Save captured image
        image_data = base64.b64decode(image_data.split(',')[1])
        image_path = image_service.save_image(image_data)
        
        # Detect faces in image
        faces = face_service.detect_faces(image_path)
        if not faces:
            image_service.delete_image(image_path)
            return jsonify({
                'success': False,
                'message': 'No face detected in image'
            })
        
        if len(faces) > 1:
            image_service.delete_image(image_path)
            return jsonify({
                'success': False,
                'message': 'Multiple faces detected. Please provide a clear photo with only your face'
            })
        
        # Verify face
        match = face_service.verify_face(faces[0], current_user.id)
        
        # Clean up temporary image
        image_service.delete_image(image_path)
        
        if match:
            return jsonify({
                'success': True,
                'message': 'Face verification successful',
                'confidence': match['confidence']
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Face verification failed'
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@recognition.route('/recognize', methods=['POST'])
@login_required
def recognize():
    """
    Recognize faces in image.
    """
    if not current_user.is_teacher():
        return jsonify({
            'success': False,
            'message': 'Access denied'
        })
    
    image_data = request.form.get('image')
    if not image_data:
        return jsonify({
            'success': False,
            'message': 'No image provided'
        })
    
    try:
        # Save captured image
        image_data = base64.b64decode(image_data.split(',')[1])
        image_path = image_service.save_image(image_data)
        
        # Detect faces in image
        faces = face_service.detect_faces(image_path)
        if not faces:
            image_service.delete_image(image_path)
            return jsonify({
                'success': False,
                'message': 'No faces detected in image'
            })
        
        # Recognize each face
        matches = []
        for face in faces:
            match = face_service.search_face(face)
            if match:
                student = db.get_user_by_id(match['student_id'])
                if student:
                    matches.append({
                        'student_id': student['id'],
                        'name': f"{student['first_name']} {student['last_name']}",
                        'class_name': student['class_name'],
                        'division': student['division'],
                        'confidence': match['confidence']
                    })
        
        # Clean up temporary image
        image_service.delete_image(image_path)
        
        return jsonify({
            'success': True,
            'matches': matches
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }) 