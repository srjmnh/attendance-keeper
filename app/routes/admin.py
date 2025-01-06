from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app.services.db_service import DatabaseService
from app.services.face_service import FaceService
import re

admin = Blueprint('admin', __name__)
db = DatabaseService()
face_service = FaceService()

def admin_required(f):
    """Decorator to require admin role for routes"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Access denied. Administrators only.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin.route('/users')
@login_required
@admin_required
def users():
    """
    Manage users.
    """
    role = request.args.get('role')
    status = request.args.get('status')
    search = request.args.get('search')
    
    users = db.get_users(role=role, status=status, search=search)
    return render_template('admin/users.html', users=users)

@admin.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """
    Create a new user.
    """
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        role = request.form.get('role')
        class_name = request.form.get('class_name')
        division = request.form.get('division')
        
        # Validate email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Please enter a valid email address.', 'danger')
            return redirect(url_for('admin.create_user'))
        
        # Check if email already exists
        if db.get_user_by_email(email):
            flash('Email address already exists.', 'danger')
            return redirect(url_for('admin.create_user'))
        
        # Validate password strength
        if not re.match(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$", password):
            flash('Password must be at least 8 characters long and contain letters and numbers.', 'danger')
            return redirect(url_for('admin.create_user'))
        
        # Create user object
        user = {
            'email': email,
            'password': generate_password_hash(password),
            'first_name': first_name,
            'last_name': last_name,
            'role': role,
            'status': 'active'
        }
        
        # Add class and division for students
        if role == 'student':
            if not class_name or not division:
                flash('Please select class and division for student.', 'danger')
                return redirect(url_for('admin.create_user'))
            user['class_name'] = class_name
            user['division'] = division
        
        try:
            user_id = db.create_user(user)
            if user_id:
                flash('User created successfully.', 'success')
                return redirect(url_for('admin.users'))
        except Exception as e:
            flash('An error occurred while creating the user.', 'danger')
            return redirect(url_for('admin.create_user'))
    
    return render_template('admin/create_user.html')

@admin.route('/users/edit/<user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """
    Edit an existing user.
    """
    user = db.get_user_by_id(user_id)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin.users'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        role = request.form.get('role')
        status = request.form.get('status')
        class_name = request.form.get('class_name')
        division = request.form.get('division')
        new_password = request.form.get('new_password')
        
        # Validate email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Please enter a valid email address.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))
        
        # Check if email already exists (excluding current user)
        existing_user = db.get_user_by_email(email)
        if existing_user and existing_user['id'] != user_id:
            flash('Email address already exists.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))
        
        # Create updates object
        updates = {
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'role': role,
            'status': status
        }
        
        # Add class and division for students
        if role == 'student':
            if not class_name or not division:
                flash('Please select class and division for student.', 'danger')
                return redirect(url_for('admin.edit_user', user_id=user_id))
            updates['class_name'] = class_name
            updates['division'] = division
        
        # Update password if provided
        if new_password:
            if not re.match(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$", new_password):
                flash('Password must be at least 8 characters long and contain letters and numbers.', 'danger')
                return redirect(url_for('admin.edit_user', user_id=user_id))
            updates['password'] = generate_password_hash(new_password)
        
        try:
            db.update_user(user_id, updates)
            flash('User updated successfully.', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            flash('An error occurred while updating the user.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))
    
    return render_template('admin/edit_user.html', user=user)

@admin.route('/users/delete/<user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    """
    Delete a user.
    """
    try:
        # Check if user exists
        user = db.get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Check if user has attendance records
        if db.user_has_attendance(user_id):
            return jsonify({
                'success': False,
                'message': 'Cannot delete user with attendance records'
            })
        
        # Delete user's face data if exists
        if user['role'] == 'student':
            face_service.delete_face(user_id)
        
        # Delete user
        db.delete_user(user_id)
        return jsonify({
            'success': True,
            'message': 'User deleted successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    """
    Manage system settings.
    """
    if request.method == 'POST':
        settings = {
            'site_name': request.form.get('site_name'),
            'face_recognition_threshold': float(request.form.get('face_recognition_threshold', 80)),
            'attendance_edit_window': int(request.form.get('attendance_edit_window', 24)),
            'enable_email_notifications': request.form.get('enable_email_notifications') == 'on',
            'enable_face_recognition': request.form.get('enable_face_recognition') == 'on'
        }
        
        try:
            db.update_settings(settings)
            flash('Settings updated successfully.', 'success')
            return redirect(url_for('admin.settings'))
        except Exception as e:
            flash('An error occurred while updating settings.', 'danger')
            return redirect(url_for('admin.settings'))
    
    current_settings = db.get_settings()
    return render_template('admin/settings.html', settings=current_settings)

@admin.route('/logs')
@login_required
@admin_required
def logs():
    """
    View system logs.
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    level = request.args.get('level')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    logs = db.get_logs(
        page=page,
        per_page=per_page,
        level=level,
        start_date=start_date,
        end_date=end_date
    )
    
    return render_template('admin/logs.html', logs=logs) 