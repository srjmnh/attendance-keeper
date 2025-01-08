from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify, send_file
from flask_login import login_required, current_user
from app.services.db_service import DatabaseService
from app.utils.decorators import role_required
from functools import wraps
from werkzeug.security import generate_password_hash
from datetime import datetime
import pandas as pd
import io

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/')
@login_required
@role_required(['admin'])
def admin_dashboard():
    return render_template('admin/dashboard.html')

@bp.route('/users')
@login_required
@role_required(['admin'])
def manage_users():
    db = DatabaseService()
    users = db.get_all_users()
    return render_template('admin/users.html', users=users)

@bp.route('/manage_subjects', methods=['GET', 'POST'])
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
    
    # GET request - display subjects
    try:
        subjects = []
        for doc in current_app.db.collection("subjects").stream():
            subject_data = doc.to_dict()
            subjects.append({
                'id': doc.id,
                'name': subject_data.get('name', 'N/A'),
                'details': subject_data.get('details', '')
            })
        return render_template("admin/subjects.html", subjects=subjects)
    except Exception as e:
        flash(f"Error loading subjects: {str(e)}", "error")
        return render_template("admin/subjects.html", subjects=[])

@bp.route('/manage_subjects/<subject_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def delete_subject(subject_id):
    """Delete a subject"""
    try:
        current_app.db.collection("subjects").document(subject_id).delete()
        return {'message': 'Subject deleted successfully'}, 200
    except Exception as e:
        return {'error': str(e)}, 500

@bp.route('/students')
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

@bp.route('/api/students/<student_id>', methods=['GET'])
@login_required
@role_required(['admin'])
def get_student(student_id):
    """Get student details"""
    doc = current_app.db.collection('users').document(student_id).get()
    if not doc.exists:
        return jsonify({'error': 'Student not found'}), 404
    data = doc.to_dict()
    return jsonify({
        'username': data.get('username', ''),
        'student_id': data.get('student_id', '')
    })

@bp.route('/api/students/<student_id>', methods=['PUT'])
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
            
        # Validate student ID format
        student_id_new = str(data['student_id']).strip()
        if not student_id_new.isalnum():
            return jsonify({'error': 'Student ID must be alphanumeric without spaces'}), 400
            
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
            'division': division,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        student_ref.update(update_data)
        current_app.logger.info(f"Updated student {student_id}")
        
        return jsonify({'message': 'Student updated successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Error updating student: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/students/<student_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def delete_student(student_id):
    """Delete a student"""
    try:
        current_app.db.collection('users').document(student_id).delete()
        return jsonify({'message': 'Student deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/add_student', methods=['POST'])
@login_required
@role_required(['admin'])
def add_student():
    """Add a new student"""
    username = request.form.get('username')
    student_id = request.form.get('student_id')
    password = request.form.get('password')
    
    if not username or not student_id or not password:
        flash('All fields are required', 'error')
        return redirect(url_for('admin.manage_students'))
    
    # Check if username already exists
    existing = current_app.db.collection('users').where('username', '==', username).stream()
    if any(existing):
        flash('Username already exists', 'error')
        return redirect(url_for('admin.manage_students'))
    
    # Create new student
    try:
        current_app.db.collection('users').add({
            'username': username,
            'student_id': student_id,
            'password_hash': generate_password_hash(password),
            'role': 'student',
            'created_at': datetime.utcnow().isoformat()
        })
        flash('Student added successfully', 'success')
    except Exception as e:
        flash(f'Error adding student: {str(e)}', 'error')
    
    return redirect(url_for('admin.manage_students'))

@bp.route('/api/students')
@login_required
@role_required(['admin', 'teacher'])
def get_students():
    """Get all students"""
    try:
        current_app.logger.info("Fetching students from database")
        students = []
        
        # Get students collection with role filter
        students_ref = current_app.db.collection('users').where('role', '==', 'student')
        docs = students_ref.get()  # Use get() instead of stream() for better error handling
        
        if not docs:
            current_app.logger.warning("No students found in database")
            return jsonify([])
            
        for doc in docs:
            try:
                data = doc.to_dict()
                current_app.logger.debug(f"Processing student document: {doc.id}")
                
                # Extract student data with proper type checking
                student_data = {
                    'id': doc.id,
                    'name': str(data.get('name', '')),
                    'student_id': str(data.get('student_id', '')),
                    'class': int(data.get('class', 0)) or '',  # Convert to int, fallback to empty if 0
                    'division': str(data.get('division', '')).upper()
                }
                
                # Validate required fields
                if not student_data['student_id']:
                    current_app.logger.warning(f"Skipping student {doc.id} - missing student_id")
                    continue
                    
                current_app.logger.debug(f"Student data: {student_data}")
                students.append(student_data)
                
            except (ValueError, TypeError) as e:
                # Log the error but continue processing other students
                current_app.logger.error(f"Error processing student {doc.id}: {str(e)}")
                continue
        
        current_app.logger.info(f"Successfully retrieved {len(students)} students")
        return jsonify(students)
        
    except Exception as e:
        current_app.logger.error(f"Failed to fetch students: {str(e)}")
        return jsonify({'error': f"Failed to fetch students: {str(e)}"}), 500

@bp.route('/api/students/template')
@login_required
@role_required(['admin', 'teacher'])
def get_student_template():
    """Get student data template"""
    try:
        # Create Excel template with example data
        data = {
            'name': ['John Doe', 'Jane Smith'],
            'student_id': ['STU001', 'STU002'],
            'class': [10, 11],
            'division': ['A', 'B']
        }
        df = pd.DataFrame(data)
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
            # Adjust column widths
            worksheet = writer.sheets['Sheet1']
            for idx, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).apply(len).max(), len(col))
                worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2
        
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='student_template.xlsx'
        )
    except Exception as e:
        current_app.logger.error(f"Error creating template: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/students/upload', methods=['POST'])
@login_required
@role_required(['admin', 'teacher'])
def upload_students():
    """Upload student data from Excel"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Invalid file format. Please upload an Excel file'}), 400
            
        # Read Excel file
        df = pd.read_excel(file)
        required_columns = ['name', 'student_id', 'class', 'division']
        
        if not all(col in df.columns for col in required_columns):
            return jsonify({'error': 'Invalid template format. Please use the provided template'}), 400
            
        # Process each row
        success_count = 0
        error_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Validate data
                if not all(str(row[col]).strip() for col in required_columns):
                    errors.append(f"Row {index + 2}: All fields are required")
                    error_count += 1
                    continue

                # Validate student ID format (alphanumeric, no spaces)
                student_id = str(row['student_id']).strip()
                if not student_id.isalnum():
                    errors.append(f"Row {index + 2}: Student ID must be alphanumeric without spaces")
                    error_count += 1
                    continue

                # Validate class (must be between 1 and 12)
                try:
                    class_num = int(row['class'])
                    if not 1 <= class_num <= 12:
                        errors.append(f"Row {index + 2}: Class must be between 1 and 12")
                        error_count += 1
                        continue
                except ValueError:
                    errors.append(f"Row {index + 2}: Class must be a number")
                    error_count += 1
                    continue

                # Validate division (must be A, B, C, or D)
                division = str(row['division']).strip().upper()
                if division not in ['A', 'B', 'C', 'D']:
                    errors.append(f"Row {index + 2}: Division must be A, B, C, or D")
                    error_count += 1
                    continue

                student_data = {
                    'name': str(row['name']).strip(),
                    'student_id': student_id,
                    'class': class_num,
                    'division': division,
                    'role': 'student',
                    'created_at': datetime.utcnow().isoformat()
                }
                
                # Check if student already exists
                existing = current_app.db.collection('users').where('student_id', '==', student_data['student_id']).get()
                if len(list(existing)) > 0:
                    errors.append(f"Row {index + 2}: Student ID {student_id} already exists")
                    error_count += 1
                    continue
                    
                # Add new student
                current_app.db.collection('users').add(student_data)
                success_count += 1
                
            except Exception as e:
                current_app.logger.error(f"Error processing row {index + 2}: {str(e)}")
                errors.append(f"Row {index + 2}: {str(e)}")
                error_count += 1
                continue
            
        return jsonify({
            'message': f'Upload completed. {success_count} students added successfully, {error_count} errors.',
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        })
    except Exception as e:
        current_app.logger.error(f"Error uploading students: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/students', methods=['POST'])
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
            
        # Validate student ID format
        student_id = str(data['student_id']).strip()
        if not student_id.isalnum():
            return jsonify({'error': 'Student ID must be alphanumeric without spaces'}), 400
            
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