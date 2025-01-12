from flask import Blueprint, render_template, redirect, url_for, flash, current_app, jsonify, request
from flask_login import login_required, current_user
from functools import wraps

teacher_bp = Blueprint('teacher', __name__)

def teacher_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'teacher':
            flash('Access denied. Teacher privileges required.', 'error')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@teacher_bp.route('/students')
@login_required
@teacher_required
def students():
    """Display students for classes assigned to the teacher"""
    try:
        students = []
        
        # Get teacher's assigned classes
        teacher_classes = getattr(current_user, 'classes', [])
        if not teacher_classes:
            flash('No classes assigned to your account.', 'error')
            return redirect(url_for('main.dashboard'))
            
        # Get all students
        students_ref = current_app.db.collection('users').where('role', '==', 'student').get()
        
        # Filter students based on teacher's classes
        for doc in students_ref:
            student_data = doc.to_dict()
            class_division = f"{student_data.get('class')}-{student_data.get('division')}"
            
            if class_division in teacher_classes:
                student_data['doc_id'] = doc.id
                student_data['has_portal'] = True if student_data.get('email') else False
                student_data['email'] = student_data.get('email', '')
                students.append(student_data)
                
        return render_template('teacher/view_students.html', students=students)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching students: {str(e)}")
        flash('Error fetching students', 'error')
        return redirect(url_for('main.dashboard'))

@teacher_bp.route('/register/face')
@login_required
@teacher_required
def register_face():
    """Face registration page for teachers"""
    try:
        # Get teacher's assigned classes
        teacher_classes = getattr(current_user, 'classes', [])
        if not teacher_classes:
            flash('No classes assigned to your account.', 'error')
            return redirect(url_for('main.dashboard'))
            
        return render_template('recognition/register.html', assigned_classes=teacher_classes)
        
    except Exception as e:
        current_app.logger.error(f"Error loading face registration: {str(e)}")
        flash('Error loading face registration', 'error')
        return redirect(url_for('main.dashboard'))

@teacher_bp.route('/api/students/<student_id>', methods=['PUT'])
@login_required
@teacher_required
def update_student(student_id):
    """Update student details (only for assigned classes)"""
    try:
        data = request.get_json()
        
        # Get student's current data
        student_ref = current_app.db.collection('users').document(student_id)
        student = student_ref.get()
        
        if not student.exists:
            return jsonify({'error': 'Student not found'}), 404
            
        student_data = student.to_dict()
        class_division = f"{student_data.get('class')}-{student_data.get('division')}"
        
        # Verify teacher has access to this class
        if class_division not in current_user.classes:
            return jsonify({'error': 'You do not have permission to modify this student'}), 403
            
        # Update allowed fields
        update_data = {
            'name': data.get('name', student_data.get('name')),
            'student_id': data.get('student_id', student_data.get('student_id')),
            'class': data.get('class', student_data.get('class')),
            'division': data.get('division', student_data.get('division'))
        }
        
        # Verify new class assignment is allowed
        new_class_division = f"{update_data['class']}-{update_data['division']}"
        if new_class_division not in current_user.classes:
            return jsonify({'error': 'You cannot assign student to a class you do not teach'}), 403
            
        student_ref.update(update_data)
        return jsonify({'message': 'Student updated successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Error updating student: {str(e)}")
        return jsonify({'error': str(e)}), 500 

@teacher_bp.route('/view/students')
@login_required
@teacher_required
def view_students():
    """Display students for classes assigned to the teacher"""
    try:
        students = []
        
        # Get teacher's assigned classes
        teacher_classes = getattr(current_user, 'classes', [])
        if not teacher_classes:
            flash('No classes assigned to your account.', 'error')
            return redirect(url_for('main.dashboard'))
            
        # Get all students
        students_ref = current_app.db.collection('users').where('role', '==', 'student').get()
        
        # Filter students based on teacher's classes
        for doc in students_ref:
            student_data = doc.to_dict()
            class_division = f"{student_data.get('class')}-{student_data.get('division')}"
            
            if class_division in teacher_classes:
                student_data['doc_id'] = doc.id
                student_data['has_portal'] = True if student_data.get('email') else False
                student_data['email'] = student_data.get('email', '')
                students.append(student_data)
                
        return render_template('teacher/view_students.html', students=students)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching students: {str(e)}")
        flash('Error fetching students', 'error')
        return redirect(url_for('main.dashboard')) 