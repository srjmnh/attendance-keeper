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
    # Get all students from Firestore
    students_ref = current_app.db.collection('users').where('role', '==', 'student').stream()
    students = []
    for doc in students_ref:
        data = doc.to_dict()
        students.append({
            'id': doc.id,
            'username': data.get('username', ''),
            'student_id': data.get('student_id', '')
        })
    return render_template('admin/students.html', students=students)

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
    data = request.json
    update_data = {
        'username': data.get('username'),
        'student_id': data.get('student_id'),
        'updated_at': datetime.utcnow().isoformat()
    }
    
    # Update password if provided
    if data.get('password'):
        update_data['password_hash'] = generate_password_hash(data['password'])
    
    try:
        current_app.db.collection('users').document(student_id).update(update_data)
        return jsonify({'message': 'Student updated successfully'})
    except Exception as e:
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
        students = []
        students_ref = current_app.db.collection('users').where('role', '==', 'student').stream()
        
        for doc in students_ref:
            data = doc.to_dict()
            students.append({
                'id': doc.id,
                'name': data.get('name', ''),
                'student_id': data.get('student_id', ''),
                'class': data.get('class', ''),
                'division': data.get('division', '')
            })
        
        return jsonify(students)
    except Exception as e:
        current_app.logger.error(f"Error getting students: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/api/students/template')
@login_required
@role_required(['admin', 'teacher'])
def get_student_template():
    """Get student data template"""
    try:
        # Create Excel template
        df = pd.DataFrame(columns=[
            'name',
            'student_id',
            'class',
            'division'
        ])
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
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
        for _, row in df.iterrows():
            student_data = {
                'name': row['name'],
                'student_id': str(row['student_id']),
                'class': int(row['class']),
                'division': str(row['division']),
                'role': 'student',
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Check if student already exists
            existing = current_app.db.collection('users').where('student_id', '==', str(row['student_id'])).get()
            if len(list(existing)) > 0:
                continue  # Skip existing students
                
            # Add new student
            current_app.db.collection('users').add(student_data)
            
        return jsonify({'message': 'Students uploaded successfully'})
    except Exception as e:
        current_app.logger.error(f"Error uploading students: {str(e)}")
        return jsonify({'error': str(e)}), 500 