from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from app.models.user import User
from app.services.firebase_service import get_user_by_email, get_user_by_id, update_user
from app.utils.decorators import anonymous_required
from app.services.storage_service import upload_file, delete_file

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
@anonymous_required
def login():
    """Handle user login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember_me') else False
        
        try:
            # Get user from Firebase
            user_data = get_user_by_email(email)
            
            if not user_data:
                flash('Please check your login details and try again.', 'error')
                return redirect(url_for('auth.login'))
            
            # Verify password
            if not check_password_hash(user_data.get('password'), password):
                flash('Please check your login details and try again.', 'error')
                return redirect(url_for('auth.login'))
            
            # Create user object
            user = User(
                id=user_data.get('id'),
                email=user_data.get('email'),
                name=user_data.get('name'),
                role=user_data.get('role')
            )
            
            # Log in user
            login_user(user, remember=remember)
            
            # Get the page they wanted to access
            next_page = request.args.get('next')
            
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('main.dashboard')
            
            flash('Successfully logged in!', 'success')
            return redirect(next_page)
            
        except Exception as e:
            current_app.logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login. Please try again.', 'error')
            return redirect(url_for('auth.login'))
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash('Successfully logged out!', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET'])
@login_required
def profile():
    """Display user profile"""
    return render_template('auth/profile.html')

@auth_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Handle profile updates"""
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        
        if not name or not email:
            flash('Name and email are required.', 'error')
            return redirect(url_for('auth.profile'))
        
        # Check if email is already taken by another user
        if email != current_user.email:
            existing_user = get_user_by_email(email)
            if existing_user and existing_user.get('id') != current_user.id:
                flash('Email is already taken.', 'error')
                return redirect(url_for('auth.profile'))
        
        # Update user data
        update_data = {
            'name': name,
            'email': email,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        updated_user = update_user(current_user.id, update_data)
        
        if updated_user:
            flash('Profile updated successfully!', 'success')
        else:
            flash('Failed to update profile.', 'error')
        
        return redirect(url_for('auth.profile'))
        
    except Exception as e:
        current_app.logger.error(f"Profile update error: {str(e)}")
        flash('An error occurred while updating your profile.', 'error')
        return redirect(url_for('auth.profile'))

@auth_bp.route('/profile/avatar', methods=['POST'])
@login_required
def update_avatar():
    """Handle avatar upload"""
    try:
        if 'avatar' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['avatar']
        
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400
        
        # Validate file type
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if not '.' in file.filename or \
           file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({'error': 'Invalid file type'}), 400
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"avatars/{current_user.id}/{uuid.uuid4()}-{filename}"
        
        # Upload to storage
        avatar_url = upload_file(file, unique_filename)
        
        # Update user data with new avatar URL
        update_data = {
            'avatar_url': avatar_url,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Delete old avatar if exists
        old_avatar_url = current_user.avatar_url
        if old_avatar_url:
            try:
                delete_file(old_avatar_url)
            except Exception as e:
                current_app.logger.error(f"Error deleting old avatar: {str(e)}")
        
        updated_user = update_user(current_user.id, update_data)
        
        if not updated_user:
            return jsonify({'error': 'Failed to update avatar'}), 500
        
        return jsonify({'avatar_url': avatar_url})
        
    except Exception as e:
        current_app.logger.error(f"Avatar upload error: {str(e)}")
        return jsonify({'error': 'Failed to upload avatar'}), 500

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Handle password change"""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        try:
            # Get current user data
            user_data = get_user_by_id(current_user.id)
            
            if not user_data:
                flash('User not found.', 'error')
                return redirect(url_for('auth.change_password'))
            
            # Verify current password
            if not check_password_hash(user_data.get('password'), current_password):
                flash('Current password is incorrect.', 'error')
                return redirect(url_for('auth.change_password'))
            
            # Verify new password
            if new_password != confirm_password:
                flash('New passwords do not match.', 'error')
                return redirect(url_for('auth.change_password'))
            
            # Update password in Firebase
            update_data = {
                'password': generate_password_hash(new_password, method='sha256'),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            updated_user = update_user(current_user.id, update_data)
            
            if updated_user:
                flash('Password successfully updated!', 'success')
                return redirect(url_for('main.dashboard'))
            else:
                flash('Failed to update password.', 'error')
                return redirect(url_for('auth.change_password'))
            
        except Exception as e:
            current_app.logger.error(f"Password change error: {str(e)}")
            flash('An error occurred while changing password. Please try again.', 'error')
            return redirect(url_for('auth.change_password'))
    
    return render_template('auth/change_password.html') 