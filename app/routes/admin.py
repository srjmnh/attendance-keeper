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
@role_required(['admin', 'teacher'])
def manage_students():
    """Display student management page"""
    try:
        current_app.logger.info("Fetching students for management page")
        students = []
        
        # Get students collection with role filter
        students_ref = current_app.db.collection('users').where('role', '==', 'student')
        
        # For teachers, filter students based on their assigned classes
        if current_user.role == 'teacher':
            assigned_classes = current_user.classes
            assigned_class_numbers = list(set(class_div.split('-')[0] for class_div in assigned_classes))
            assigned_divisions = list(set(class_div.split('-')[1] for class_div in assigned_classes))
            
            # Get students in assigned classes and divisions
            docs = students_ref.get()
            for doc in docs:
                data = doc.to_dict()
                class_str = str(data.get('class', ''))
                division = str(data.get('division', '')).upper()
                
                # Check if student's class and division match teacher's assignments
                if (class_str in assigned_class_numbers and 
                    division in assigned_divisions and 
                    f"{class_str}-{division}" in assigned_classes):
                    student_data = {
                        'id': doc.id,
                        'name': str(data.get('name', '')),
                        'student_id': str(data.get('student_id', '')),
                        'class': int(data.get('class', 0)) or '',
                        'division': division
                    }
                    students.append(student_data)
        else:
            # For admin, get all students
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
            
        # Check if student exists
        student_ref = current_app.db.collection('users').document(student_id)
        student_doc = student_ref.get()
        if not student_doc.exists:
            return jsonify({'error': 'Student not found'}), 404
            
        # For teachers, validate that they can manage this class
        if current_user.role == 'teacher':
            # Check if teacher can manage the current class
            student_data = student_doc.to_dict()
            current_class = f"{student_data.get('class')}-{student_data.get('division')}"
            if current_class not in current_user.classes:
                return jsonify({'error': 'You are not authorized to manage this student'}), 403
                
            # Check if teacher can manage the new class
            new_class = f"{class_num}-{division}"
            if new_class not in current_user.classes:
                return jsonify({'error': 'You are not authorized to move students to this class'}), 403
            
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
@role_required(['admin'])
def add_student():
    """Add a new user account"""
    try:
        data = request.json
        current_app.logger.info(f"Received data for add_user: {data}")
        
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        role = data.get('role')
        student_id = data.get('student_id')
        classes = data.get('classes', [])

        # Log the required fields
        current_app.logger.info(f"Required fields: email={email}, name={name}, role={role}, student_id={student_id}, classes={classes}, password={'set' if password else 'not set'}")

        # Validate required fields
        if not all([email, password, name, role]):
            missing = [field for field, value in {'email': email, 'password': password, 'name': name, 'role': role}.items() if not value]
            error_msg = f"Missing required fields: {', '.join(missing)}"
            current_app.logger.error(error_msg)
            return jsonify({'error': error_msg}), 400

        # Validate student_id for student role
        if role == 'student' and not student_id:
            error_msg = "Student ID is required for student accounts"
            current_app.logger.error(error_msg)
            return jsonify({'error': error_msg}), 400

        # Validate classes for teacher role
        if role == 'teacher' and not classes:
            error_msg = "At least one class must be assigned to teacher accounts"
            current_app.logger.error(error_msg)
            return jsonify({'error': error_msg}), 400

        # Check if student_id exists (only for student role)
        if role == 'student':
            existing = current_app.db.collection('users').where('student_id', '==', student_id).get()
            if len(list(existing)) > 0:
                return jsonify({'error': 'Student ID already exists'}), 400

        try:
            # Create user in Firebase Auth
            current_app.logger.info(f"Creating Firebase Auth user with email: {email}")
            user_kwargs = {
                'email': email,
                'password': password,
                'display_name': name
            }
            user = auth.create_user(**user_kwargs)
            current_app.logger.info(f"Created Firebase Auth user with UID: {user.uid}")
            
            # Add custom claims based on role
            claims = {'role': role}
            if role == 'student':
                claims['student_id'] = student_id
            elif role == 'teacher':
                claims['classes'] = classes
            current_app.logger.info(f"Setting custom claims for user {user.uid}: {claims}")
            auth.set_custom_user_claims(user.uid, claims)
            
            # Add user to Firestore
            user_data = {
                'email': email,
                'name': name,
                'role': role,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Add role-specific data
            if role == 'student':
                user_data['student_id'] = student_id
            elif role == 'teacher':
                user_data['classes'] = classes
            
            current_app.logger.info(f"Adding user data to Firestore: {user_data}")
            current_app.db.collection('users').document(user.uid).set(user_data)
            return jsonify({'message': f'{role.title()} account created successfully', 'id': user.uid}), 201

        except firebase_admin.auth.EmailAlreadyExistsError:
            current_app.logger.error(f"Email {email} already exists")
            return jsonify({'error': 'Email already exists'}), 400
        except Exception as e:
            current_app.logger.error(f"Firebase error: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    except Exception as e:
        current_app.logger.error(f"Error creating user account: {str(e)}")
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

@admin_bp.route('/api/subjects')
@login_required
@role_required(['admin', 'teacher'])
def get_subjects():
    """Get all subjects or teacher-specific subjects"""
    try:
        subjects = []
        subjects_ref = current_app.db.collection('subjects')
        
        if current_user.role == 'admin':
            # Admin sees all subjects
            docs = subjects_ref.stream()
            subjects = [{
                'id': doc.id,
                'name': doc.to_dict().get('name', '')
            } for doc in docs]
        else:
            # Teachers see only their assigned subjects
            for class_id in current_user.classes:
                doc = subjects_ref.document(class_id).get()
                if doc.exists:
                    subjects.append({
                        'id': doc.id,
                        'name': doc.to_dict().get('name', '')
                    })
        
        return jsonify({'subjects': subjects})
    except Exception as e:
        current_app.logger.error(f"Error getting subjects: {str(e)}")
        return jsonify({'error': str(e)}), 500 