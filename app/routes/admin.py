from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from app.services.db_service import DatabaseService
from app.utils.decorators import admin_required

admin = Blueprint('admin', __name__)

@admin.route('/admin/users')
@login_required
@admin_required
def manage_users():
    """Manage users page"""
    try:
        db = DatabaseService()
        users = db.get_all_users()
        return render_template('admin/users.html', users=users)
    except Exception as e:
        current_app.logger.error(f"Error in manage users route: {str(e)}")
        flash('An error occurred while loading users.', 'danger')
        return redirect(url_for('main.index'))

@admin.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create new user"""
    if request.method == 'POST':
        try:
            db = DatabaseService()
            user_data = {
                'email': request.form.get('email'),
                'password': request.form.get('password'),
                'first_name': request.form.get('first_name'),
                'last_name': request.form.get('last_name'),
                'role': request.form.get('role'),
                'class_name': request.form.get('class_name'),
                'division': request.form.get('division')
            }
            
            # Validate required fields
            if not all([user_data['email'], user_data['password'], 
                       user_data['first_name'], user_data['role']]):
                flash('Please fill in all required fields.', 'danger')
                return render_template('admin/create_user.html')
            
            # Create user
            db.create_user(user_data)
            flash('User created successfully.', 'success')
            return redirect(url_for('admin.manage_users'))
            
        except Exception as e:
            current_app.logger.error(f"Error creating user: {str(e)}")
            flash('An error occurred while creating the user.', 'danger')
            return render_template('admin/create_user.html')
    
    return render_template('admin/create_user.html')

@admin.route('/admin/users/<user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user"""
    try:
        db = DatabaseService()
        if request.method == 'POST':
            user_data = {
                'email': request.form.get('email'),
                'first_name': request.form.get('first_name'),
                'last_name': request.form.get('last_name'),
                'role': request.form.get('role'),
                'class_name': request.form.get('class_name'),
                'division': request.form.get('division')
            }
            
            # Update password only if provided
            password = request.form.get('password')
            if password:
                user_data['password'] = password
            
            # Update user
            db.update_user(user_id, user_data)
            flash('User updated successfully.', 'success')
            return redirect(url_for('admin.manage_users'))
        
        # Get user data for form
        user = db.get_user_by_id(user_id)
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('admin.manage_users'))
            
        return render_template('admin/edit_user.html', user=user)
        
    except Exception as e:
        current_app.logger.error(f"Error editing user: {str(e)}")
        flash('An error occurred while editing the user.', 'danger')
        return redirect(url_for('admin.manage_users'))

@admin.route('/admin/users/<user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete user"""
    try:
        db = DatabaseService()
        db.delete_user(user_id)
        flash('User deleted successfully.', 'success')
    except Exception as e:
        current_app.logger.error(f"Error deleting user: {str(e)}")
        flash('An error occurred while deleting the user.', 'danger')
    return redirect(url_for('admin.manage_users'))

@admin.route('/admin/subjects')
@login_required
@admin_required
def manage_subjects():
    """Manage subjects page"""
    try:
        db = DatabaseService()
        subjects = db.get_all_subjects()
        teachers = db.get_all_teachers()
        return render_template('admin/subjects.html', subjects=subjects, teachers=teachers)
    except Exception as e:
        current_app.logger.error(f"Error in manage subjects route: {str(e)}")
        flash('An error occurred while loading subjects.', 'danger')
        return redirect(url_for('main.index'))

@admin.route('/admin/subjects/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_subject():
    """Create new subject"""
    try:
        db = DatabaseService()
        if request.method == 'POST':
            subject_data = {
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'teacher_id': request.form.get('teacher_id'),
                'class_name': request.form.get('class_name'),
                'division': request.form.get('division')
            }
            
            # Validate required fields
            if not all([subject_data['name'], subject_data['teacher_id'], 
                       subject_data['class_name'], subject_data['division']]):
                flash('Please fill in all required fields.', 'danger')
                teachers = db.get_all_teachers()
                return render_template('admin/create_subject.html', teachers=teachers)
            
            # Create subject
            db.create_subject(subject_data)
            flash('Subject created successfully.', 'success')
            return redirect(url_for('admin.manage_subjects'))
        
        teachers = db.get_all_teachers()
        return render_template('admin/create_subject.html', teachers=teachers)
        
    except Exception as e:
        current_app.logger.error(f"Error creating subject: {str(e)}")
        flash('An error occurred while creating the subject.', 'danger')
        return redirect(url_for('admin.manage_subjects'))

@admin.route('/admin/subjects/<subject_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_subject(subject_id):
    """Edit subject"""
    try:
        db = DatabaseService()
        if request.method == 'POST':
            subject_data = {
                'name': request.form.get('name'),
                'description': request.form.get('description'),
                'teacher_id': request.form.get('teacher_id'),
                'class_name': request.form.get('class_name'),
                'division': request.form.get('division')
            }
            
            # Update subject
            db.update_subject(subject_id, subject_data)
            flash('Subject updated successfully.', 'success')
            return redirect(url_for('admin.manage_subjects'))
        
        # Get subject and teachers data for form
        subject = db.get_subject_by_id(subject_id)
        if not subject:
            flash('Subject not found.', 'danger')
            return redirect(url_for('admin.manage_subjects'))
            
        teachers = db.get_all_teachers()
        return render_template('admin/edit_subject.html', subject=subject, teachers=teachers)
        
    except Exception as e:
        current_app.logger.error(f"Error editing subject: {str(e)}")
        flash('An error occurred while editing the subject.', 'danger')
        return redirect(url_for('admin.manage_subjects'))

@admin.route('/admin/subjects/<subject_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_subject(subject_id):
    """Delete subject"""
    try:
        db = DatabaseService()
        db.delete_subject(subject_id)
        flash('Subject deleted successfully.', 'success')
    except Exception as e:
        current_app.logger.error(f"Error deleting subject: {str(e)}")
        flash('An error occurred while deleting the subject.', 'danger')
    return redirect(url_for('admin.manage_subjects')) 