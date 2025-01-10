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

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
@role_required(['admin'])
def admin_dashboard():
    """Admin dashboard view"""
    return render_template('admin/dashboard.html')

@admin_bp.route('/manage/students')
@login_required
@role_required(['admin'])
def manage_students():
    """Display student management page"""
    try:
        current_app.logger.info("Fetching students for management page")
        students = []
        
        # Get students collection with role filter
        students_ref = current_app.db.collection('users').where('role', '==', 'student')
        docs = students_ref.get()
        
        for doc in docs:
            data = doc.to_dict()
            student_data = {
                'id': doc.id,
                'name': str(data.get('name', '')),
                'student_id': str(data.get('student_id', '')),
                'class': int(data.get('class', 0)) or '',
                'division': str(data.get('division', '')).upper()
            }
            students.append(student_data)
            
        current_app.logger.info(f"Found {len(students)} students")
        return render_template('admin/students.html', students=students)
        
    except Exception as e:
        current_app.logger.error(f"Error loading students page: {str(e)}")
        flash('Failed to load students. Please try again.', 'error')
        return render_template('admin/students.html', students=[])

@admin_bp.route('/manage/subjects', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def manage_subjects():
    """Manage subjects (add, edit, view)"""
    if request.method == "POST":
        # Handle form submission for adding or updating a subject
        subject_id = request.form.get("subject_id")
        subject_name = request.form.get("subject_name")
        subject_details = request.form.get("subject_details")

        if not subject_name:
            flash("Subject name is required.", "error")
            return redirect(url_for('admin.manage_subjects'))

        try:
            if subject_id:
                # Update existing subject
                subject_ref = current_app.db.collection("subjects").document(subject_id)
                subject_ref.update({
                    "name": subject_name,
                    "details": subject_details
                })
                flash("Subject updated successfully.", "success")
            else:
                # Add new subject
                current_app.db.collection("subjects").add({
                    "name": subject_name,
                    "details": subject_details
                })
                flash("Subject added successfully.", "success")
        except Exception as e:
            flash(f"Error managing subject: {str(e)}", "error")
        
        return redirect(url_for('admin.manage_subjects'))
    else:
        # Handle GET request
        subjects_ref = current_app.db.collection('subjects').stream()
        subjects = [{
            'id': doc.id,
            'name': doc.to_dict().get('name', '')
        } for doc in subjects_ref]
        return render_template('admin/subjects.html', subjects=subjects)

@admin_bp.route('/manage/users')
@login_required
@role_required(['admin'])
def manage_users():
    """Display user management page"""
    try:
        current_app.logger.info("Fetching users for management page")
        users = []
        
        # Get all users
        users_ref = current_app.db.collection('users')
        docs = users_ref.get()
        
        for doc in docs:
            data = doc.to_dict()
            user_data = {
                'id': doc.id,
                'email': str(data.get('email', '')),
                'name': str(data.get('name', '')),
                'role': str(data.get('role', '')),
                'classes': data.get('classes', []),
                'student_id': str(data.get('student_id', ''))
            }
            users.append(user_data)
            
        current_app.logger.info(f"Found {len(users)} users")
        return render_template('admin/users.html', users=users)
        
    except Exception as e:
        current_app.logger.error(f"Error loading users page: {str(e)}")
        flash('Failed to load users. Please try again.', 'error')
        return render_template('admin/users.html', users=[])

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
@role_required(['admin'])
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
            
        # Check if student exists
        student_ref = current_app.db.collection('users').document(student_id)
        if not student_ref.get().exists:
            return jsonify({'error': 'Student not found'}), 404
            
        # Check if new student ID conflicts with existing one (excluding current student)
        if student_id_new != data.get('student_id'):
            existing = current_app.db.collection('users').where('student_id', '==', student_id_new).get()
            if len(list(existing)) > 0:
                return jsonify({'error': 'Student ID already exists'}), 400
        
        # Update student data
        update_data = {
            'name': str(data['name']).strip(),
            'student_id': student_id_new,
            'class': class_num,
            'division': division
        }
        student_ref.update(update_data)
        return jsonify({'message': 'Student updated successfully.'}), 200
        
    except Exception as e:
        current_app.logger.error(f"Error updating student: {str(e)}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/students', methods=['POST'])
@login_required
@role_required(['admin'])
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
@role_required(['admin'])
def add_student_form():
    data = request.form
    email = data.get('email')
    password = data.get('password')
    student_id = data.get('student_id')

    # Validate if student_id exists
    db_service = DatabaseService()
    student = db_service.get_student_by_id(student_id)
    if not student:
        return jsonify({'error': 'There is no such student.'}), 400

    try:
        # Create user in Firebase Auth
        user = auth.create_user(
            email=email,
            password=password,
            custom_claims={'role': 'student', 'student_id': student_id}
        )
        # Add user to Firestore without including the password
        db_service.add_user(user.uid, email, student['name'], 'student', student_id)
        return jsonify({'message': 'Student account created successfully.'}), 201
    except firebase_admin.auth.EmailAlreadyExistsError:
        return jsonify({'error': 'Email already exists.'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500 

@admin_bp.route('/teachers', methods=['POST'])
@login_required
@role_required(['admin'])
def add_teacher():
    data = request.form
    email = data.get('email')
    password = data.get('password')
    classes = data.getlist('classes')  # Assuming multiple classes can be assigned

    # Validate if classes exist
    db_service = DatabaseService()
    valid_classes = db_service.get_all_classes()
    for cls in classes:
        if cls not in valid_classes:
            return jsonify({'error': f'Class {cls} does not exist.'}), 400

    try:
        # Create user in Firebase Auth
        user = auth.create_user(
            email=email,
            password=password,
            custom_claims={'role': 'teacher', 'classes': classes}
        )
        # Optionally, add user to Firestore
        db_service.add_user(user.uid, email, data.get('name'), 'teacher', classes=classes)
        return jsonify({'message': 'Teacher account created successfully.'}), 201
    except firebase_admin.auth.EmailAlreadyExistsError:
        return jsonify({'error': 'Email already exists.'}), 400
    except Exception as e:
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
        data = request.get_json()
        doc_ref = current_app.db.collection('users').document(user_id)
        
        if not doc_ref.get().exists:
            return jsonify({'error': 'User not found'}), 404
        
        # Handle password update
        if data.get('password'):
            data['password_hash'] = generate_password_hash(data['password'])
            del data['password']
        
        # Update timestamp
        data['updated_at'] = datetime.utcnow().isoformat()
        
        # Update user
        doc_ref.update(data)
        
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