from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify, send_file
from flask_login import login_required, current_user
from app.services.db_service import DatabaseService
from app.utils.decorators import role_required
from functools import wraps
from werkzeug.security import generate_password_hash
from datetime import datetime
import pandas as pd
import io
import firebase_admin
from firebase_admin import auth
from firebase_admin import firestore

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
@role_required(['admin'])
def admin_dashboard():
    """Admin dashboard view"""
    return render_template('admin/dashboard.html')

@admin_bp.route('/manage/students')
@login_required
def manage_students():
    if not current_user.role == 'admin':
        flash('Unauthorized access', 'error')
        return redirect(url_for('main.dashboard'))
        
    try:
        current_app.logger.info("Fetching students from users collection")
        # Get all students from users collection where role is student
        students_ref = current_app.db.collection('users').where('role', '==', 'student').get()
        students = []
        
        for doc in students_ref:
            student_data = doc.to_dict()
            student_data['doc_id'] = doc.id
            student_data['has_portal'] = True  # Since we're getting from users collection, they all have portal accounts
            student_data['email'] = student_data.get('email', '')
            students.append(student_data)
            
        current_app.logger.info(f"Found {len(students)} students")
        return render_template('admin/students.html', students=students)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching students: {str(e)}")
        flash('Error fetching students', 'error')
        return redirect(url_for('main.dashboard'))

@admin_bp.route('/manage/subjects', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def manage_subjects():
    """Manage subjects (add, edit, view)"""
    if request.method == 'POST':
        try:
            data = request.json
            name = data.get('name')
            class_id = data.get('class_id')  # Format: "1-A", "2-B", etc.
            
            if not name or not class_id:
                return jsonify({'error': 'Subject name and class are required'}), 400
                
            # Add subject to database
            subject_data = {
                'name': name,
                'class_id': class_id,
                'created_at': datetime.utcnow().isoformat()
            }
            
            doc_ref = current_app.db.collection('subjects').add(subject_data)
            return jsonify({
                'message': 'Subject added successfully',
                'id': doc_ref[1].id
            }), 201
            
        except Exception as e:
            current_app.logger.error(f"Error adding subject: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    # GET request - return template
    return render_template('admin/subjects.html')

@admin_bp.route('/manage/teachers')
@login_required
@role_required(['admin'])
def manage_teachers():
    """Display teacher management page"""
    try:
        current_app.logger.info("Fetching teachers for management page")
        teachers = []
        
        # Get only teacher users
        teachers_ref = current_app.db.collection('users').where('role', '==', 'teacher')
        docs = teachers_ref.get()
        
        for doc in docs:
            data = doc.to_dict()
            teacher_data = {
                'id': doc.id,
                'email': str(data.get('email', '')),
                'name': str(data.get('name', '')),
                'classes': data.get('classes', []),
                'created_at': data.get('created_at', '')
            }
            teachers.append(teacher_data)
            
        current_app.logger.info(f"Found {len(teachers)} teachers")
        return render_template('admin/teachers.html', teachers=teachers)
        
    except Exception as e:
        current_app.logger.error(f"Error loading teachers page: {str(e)}")
        flash('Failed to load teachers. Please try again.', 'error')
        return render_template('admin/teachers.html', teachers=[])

@admin_bp.route('/manage_subjects/<subject_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def delete_subject(subject_id):
    """Delete a subject"""
    try:
        current_app.db.collection("subjects").document(subject_id).delete()
        return {'message': 'Subject deleted successfully'}, 200
    except Exception as e:
        return {'error': str(e)}, 500

@admin_bp.route('/api/students/<student_id>', methods=['PUT'])
@login_required
@role_required(['admin', 'teacher'])
def update_student(student_id):
    """Update student details"""
    try:
        data = request.json
        current_app.logger.info(f"Updating student {student_id} with data: {data}")
        
        # Validate required fields
        required_fields = ['name', 'student_id', 'class', 'division']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Validate student ID format (allow letters, numbers, and common separators)
        student_id_new = str(data['student_id']).strip()
        if not student_id_new or len(student_id_new) > 20:  # Basic length check
            return jsonify({'error': 'Student ID must be between 1 and 20 characters'}), 400
            
        # Validate class
        try:
            class_num = int(data['class'])
            if not 1 <= class_num <= 12:
                return jsonify({'error': 'Class must be between 1 and 12'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid class number'}), 400
            
        # Validate division
        division = str(data['division']).strip().upper()
        if division not in ['A', 'B', 'C', 'D']:
            return jsonify({'error': 'Division must be A, B, C, or D'}), 400
            
        # Get student document directly by document ID
        student_ref = current_app.db.collection('users').document(student_id)
        student_doc = student_ref.get()
        
        if not student_doc.exists:
            current_app.logger.error(f"Student not found with document ID: {student_id}")
            return jsonify({'error': 'Student not found'}), 404
            
        student_data = student_doc.to_dict()
            
        # For teachers, validate that they can manage this class
        if current_user.role == 'teacher':
            # Check if teacher can manage the current class
            current_class = f"{student_data.get('class')}-{student_data.get('division')}"
            if current_class not in current_user.classes:
                return jsonify({'error': 'You are not authorized to manage this student'}), 403
                
            # Check if teacher can manage the new class
            new_class = f"{class_num}-{division}"
            if new_class not in current_user.classes:
                return jsonify({'error': 'You are not authorized to move students to this class'}), 403
            
        # Check if new student ID conflicts with existing one (excluding current student)
        if student_id_new != student_data.get('student_id'):
            existing = current_app.db.collection('users').where('student_id', '==', student_id_new).where('role', '==', 'student').get()
            if len(list(existing)) > 0:
                return jsonify({'error': 'Student ID already exists'}), 400
        
        # Update student data
        update_data = {
            'name': str(data['name']).strip(),
            'student_id': student_id_new,
            'class': class_num,
            'division': division,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        student_ref.update(update_data)
        current_app.logger.info(f"Successfully updated student {student_id}")
        return jsonify({'message': 'Student updated successfully.'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating student: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/students', methods=['POST'])
@login_required
@role_required(['admin', 'teacher'])
def create_student():
    """Create a new student"""
    try:
        data = request.json
        current_app.logger.info(f"Creating new student with data: {data}")
        
        # Validate required fields
        required_fields = ['name', 'student_id', 'class', 'division']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Validate student ID format (allow letters, numbers, and common separators)
        student_id = str(data['student_id']).strip()
        if not student_id or len(student_id) > 20:  # Basic length check
            return jsonify({'error': 'Student ID must be between 1 and 20 characters'}), 400
            
        # Validate class
        try:
            class_num = int(data['class'])
            if not 1 <= class_num <= 12:
                return jsonify({'error': 'Class must be between 1 and 12'}), 400
        except ValueError:
            return jsonify({'error': 'Invalid class number'}), 400
            
        # Validate division
        division = str(data['division']).strip().upper()
        if division not in ['A', 'B', 'C', 'D']:
            return jsonify({'error': 'Division must be A, B, C, or D'}), 400
            
        # For teachers, validate that they can manage this class
        if current_user.role == 'teacher':
            class_division = f"{class_num}-{division}"
            if class_division not in current_user.classes:
                return jsonify({'error': 'You are not authorized to manage students in this class'}), 403
            
        # Check if student ID already exists
        existing = current_app.db.collection('users').where('student_id', '==', student_id).get()
        if len(list(existing)) > 0:
            return jsonify({'error': 'Student ID already exists'}), 400
            
        # Create student document
        student_data = {
            'name': str(data['name']).strip(),
            'student_id': student_id,
            'class': class_num,
            'division': division,
            'role': 'student',
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Add to database
        doc_ref = current_app.db.collection('users').add(student_data)
        current_app.logger.info(f"Created student with ID: {doc_ref[1].id}")
        
        return jsonify({'message': 'Student created successfully', 'id': doc_ref[1].id}), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating student: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/add_student', methods=['POST'])
@login_required
def add_student():
    if not current_user.role == 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'name', 'role', 'student_id']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Check if email already exists
        user_ref = current_app.db.collection('users').where('email', '==', data['email']).get()
        if len(list(user_ref)) > 0:
            return jsonify({'error': 'Email already exists'}), 400
            
        # Create user in Firebase Auth
        user = auth.create_user(
            email=data['email'],
            password=data['password'],
            display_name=data['name']
        )
        
        # Get the student document
        student_ref = current_app.db.collection('students').where('student_id', '==', data['student_id']).get()
        if not student_ref:
            return jsonify({'error': 'Student not found'}), 404
            
        student_doc = list(student_ref)[0]
        student_data = student_doc.to_dict()
        
        # Create user document in Firestore
        user_data = {
            'uid': user.uid,
            'email': data['email'],
            'name': data['name'],
            'role': 'student',
            'student_id': data['student_id'],
            'class': student_data.get('class'),
            'division': student_data.get('division'),
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        # Update student document with email
        student_doc.reference.update({
            'email': data['email']
        })
        
        # Save user data
        current_app.db.collection('users').document(user.uid).set(user_data)
        
        return jsonify({
            'message': 'Student portal account created successfully',
            'uid': user.uid
        })
        
    except Exception as e:
        print(f"Error creating student portal account: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/teachers', methods=['POST'])
@login_required
@role_required(['admin'])
def add_teacher():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        classes = data.get('classes', [])  # List of class IDs (e.g., ["1-A", "1-B"])

        # Validate required fields
        if not all([name, email, password]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Validate classes
        if not classes:
            return jsonify({'error': 'At least one class must be assigned'}), 400

        # Check if email already exists
        existing_user = current_app.db.collection('users').where('email', '==', email).get()
        if len(list(existing_user)) > 0:
            return jsonify({'error': 'Email already exists'}), 400

        # Hash the password
        password_hash = generate_password_hash(password)

        # Create user document in Firestore
        user_data = {
            'name': name,
            'email': email,
            'password_hash': password_hash,
            'role': 'teacher',
            'classes': classes,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        # Add user to Firestore
        doc_ref = current_app.db.collection('users').document()
        doc_ref.set(user_data)

        return jsonify({
            'message': 'Teacher account created successfully',
            'id': doc_ref.id
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error creating teacher account: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/users', methods=['POST'])
@login_required
@role_required(['admin'])
def create_user():
    """Create a new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'name', 'password', 'role']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if user already exists
        existing_user = current_app.db.collection('users').where('email', '==', data['email']).limit(1).get()
        if len(list(existing_user)) > 0:
            return jsonify({'error': 'User with this email already exists'}), 400
        
        # Hash password
        data['password_hash'] = generate_password_hash(data['password'])
        del data['password']
        
        # Add timestamps
        data['created_at'] = datetime.utcnow().isoformat()
        data['updated_at'] = data['created_at']
        
        # Create user
        doc_ref = current_app.db.collection('users').document()
        doc_ref.set(data)
        
        return jsonify({'message': 'User created successfully', 'id': doc_ref.id}), 201
        
    except Exception as e:
        current_app.logger.error(f"Error creating user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/users/<user_id>', methods=['GET'])
@login_required
@role_required(['admin'])
def get_user(user_id):
    """Get user details"""
    try:
        doc = current_app.db.collection('users').document(user_id).get()
        if not doc.exists:
            return jsonify({'error': 'User not found'}), 404
            
        user_data = doc.to_dict()
        user_data['id'] = doc.id
        
        # Remove sensitive data
        user_data.pop('password_hash', None)
        user_data.pop('password', None)
        
        return jsonify(user_data)
        
    except Exception as e:
        current_app.logger.error(f"Error getting user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/users/<user_id>', methods=['PUT'])
@login_required
@role_required(['admin'])
def update_user(user_id):
    """Update user details"""
    try:
        data = request.json
        doc_ref = current_app.db.collection('users').document(user_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return jsonify({'error': 'User not found'}), 404
        
        # Get current user data
        current_data = doc.to_dict()
        
        # Prepare update data
        update_data = {
            'email': data.get('email'),
            'name': data.get('name'),
            'role': data.get('role'),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Handle password update
        if data.get('password'):
            update_data['password_hash'] = generate_password_hash(data['password'])
        
        # Handle role-specific data
        if data['role'] == 'student':
            if not data.get('student_id'):
                return jsonify({'error': 'Student ID is required for student accounts'}), 400
            update_data['student_id'] = data['student_id']
            # Remove classes if user was previously a teacher
            update_data['classes'] = None
        elif data['role'] == 'teacher':
            if not data.get('classes'):
                return jsonify({'error': 'At least one class must be assigned to teacher accounts'}), 400
            update_data['classes'] = data['classes']
            # Remove student_id if user was previously a student
            update_data['student_id'] = None
        else:
            # For admin role, remove both student_id and classes
            update_data['student_id'] = None
            update_data['classes'] = None
        
        # Update Firebase Auth custom claims
        try:
            claims = {'role': data['role']}
            if data['role'] == 'student':
                claims['student_id'] = data['student_id']
            elif data['role'] == 'teacher':
                claims['classes'] = data['classes']
            auth.set_custom_user_claims(user_id, claims)
        except Exception as e:
            current_app.logger.error(f"Error updating Firebase Auth claims: {str(e)}")
            return jsonify({'error': 'Failed to update user authentication'}), 500
        
        # Update Firestore document
        doc_ref.update(update_data)
        
        return jsonify({'message': 'User updated successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Error updating user: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/users/<user_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def delete_user(user_id):
    """Delete user"""
    try:
        doc_ref = current_app.db.collection('users').document(user_id)
        
        if not doc_ref.get().exists:
            return jsonify({'error': 'User not found'}), 404
        
        # Delete user
        doc_ref.delete()
        
        return jsonify({'message': 'User deleted successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Error deleting user: {str(e)}")
        return jsonify({'error': str(e)}), 500 

@admin_bp.route('/api/subjects/list', methods=['GET'])
@login_required
def list_subjects():
    """List all subjects with their class associations"""
    try:
        subjects_ref = current_app.db.collection('subjects')
        subjects = []
        
        for doc in subjects_ref.stream():
            subject_data = doc.to_dict()
            subjects.append({
                'id': doc.id,
                'name': subject_data.get('name', ''),
                'class_id': subject_data.get('class_id', '')
            })
        
        return jsonify(subjects)
    except Exception as e:
        current_app.logger.error(f"Error listing subjects: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/subjects', methods=['GET'])
@login_required
def get_subjects():
    try:
        subjects_ref = current_app.db.collection('subjects')
        subjects = subjects_ref.stream()
        subject_list = [{'id': doc.id, **doc.to_dict()} for doc in subjects]

        current_app.logger.info(f"Found {len(subject_list)} subjects")
        return jsonify({'subjects': subject_list}), 200

    except Exception as e:
        current_app.logger.error(f"Error getting subjects: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/subjects', methods=['POST'])
@login_required
@role_required(['admin'])
def create_subject():
    try:
        data = request.get_json()
        name = data.get('name')

        if not name:
            return jsonify({'error': 'Subject name is required'}), 400

        # Create subject document
        subject_data = {
            'name': name,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        # Add subject to Firestore
        doc_ref = current_app.db.collection('subjects').document()
        doc_ref.set(subject_data)

        return jsonify({
            'message': 'Subject created successfully',
            'id': doc_ref.id,
            'subject': {
                'id': doc_ref.id,
                **subject_data
            }
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error creating subject: {str(e)}")
        return jsonify({'error': str(e)}), 500 