from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from app.services.db_service import DatabaseService
from app.models.user import User
from app.forms.auth import LoginForm, ProfileForm, ChangePasswordForm
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        
        try:
            # Get user from Firestore
            users_ref = current_app.db.collection('users')
            query = users_ref.where('email', '==', email).limit(1).stream()
            
            user_doc = None
            for doc in query:
                user_doc = doc
                break
            
            if not user_doc:
                flash('Please check your login details and try again.', 'error')
                return redirect(url_for('auth.login'))
            
            user_data = user_doc.to_dict()
            user_data['id'] = user_doc.id
            
            # Verify password
            if not check_password_hash(user_data.get('password_hash', ''), password):
                flash('Please check your login details and try again.', 'error')
                return redirect(url_for('auth.login'))
            
            # Create user object with all necessary data
            user = User(
                id=user_data.get('id'),
                email=user_data.get('email'),
                name=user_data.get('name'),
                role=user_data.get('role'),
                classes=user_data.get('classes', []),
                student_id=user_data.get('student_id')
            )
            
            # Log in user
            login_user(user)
            
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
    
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login')) 

@auth_bp.route('/profile')
@login_required
def profile():
    """Display user profile settings."""
    form = ProfileForm(obj=current_user)
    return render_template('auth/profile.html', form=form)

@auth_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information."""
    form = ProfileForm()
    if form.validate_on_submit():
        try:
            # Update user document in Firestore
            user_ref = current_app.db.collection('users').document(current_user.id)
            user_ref.update({
                'name': form.name.data,
                'email': form.email.data,
                'updated_at': datetime.utcnow().isoformat()
            })
            
            # Update session user object
            current_user.name = form.name.data
            current_user.email = form.email.data
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            current_app.logger.error(f"Error updating profile: {str(e)}")
            flash('An error occurred while updating your profile.', 'error')
            return redirect(url_for('auth.profile'))
    
    for field, errors in form.errors.items():
        for error in errors:
            flash(f'{getattr(form, field).label.text}: {error}', 'error')
    return redirect(url_for('auth.profile'))

@auth_bp.route('/update_avatar', methods=['POST'])
@login_required
def update_avatar():
    """Update user's profile picture."""
    try:
        if 'avatar' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        avatar = request.files['avatar']
        if not avatar.filename:
            return jsonify({'error': 'No file selected'}), 400
            
        # TODO: Implement file upload to cloud storage
        # For now, we'll just simulate success
        avatar_url = '/static/img/default-avatar.png'
        
        # Update user document with avatar URL
        user_ref = current_app.db.collection('users').document(current_user.id)
        user_ref.update({
            'avatar_url': avatar_url,
            'updated_at': datetime.utcnow().isoformat()
        })
        
        return jsonify({
            'message': 'Avatar updated successfully',
            'avatar_url': avatar_url
        })
        
    except Exception as e:
        current_app.logger.error(f"Error updating avatar: {str(e)}")
        return jsonify({'error': str(e)}), 500 

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Handle password change requests."""
    form = ChangePasswordForm()
    
    if form.validate_on_submit():
        try:
            # Get user from Firestore
            user_ref = current_app.db.collection('users').document(current_user.id)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                flash('User not found.', 'error')
                return redirect(url_for('auth.profile'))
            
            user_data = user_doc.to_dict()
            
            # Verify current password
            if not check_password_hash(user_data.get('password_hash', ''), form.current_password.data):
                flash('Current password is incorrect.', 'error')
                return redirect(url_for('auth.change_password'))
            
            # Update password
            user_ref.update({
                'password_hash': generate_password_hash(form.new_password.data),
                'updated_at': datetime.utcnow().isoformat()
            })
            
            flash('Password changed successfully!', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            current_app.logger.error(f"Error changing password: {str(e)}")
            flash('An error occurred while changing your password.', 'error')
            return redirect(url_for('auth.change_password'))
    
    return render_template('auth/change_password.html', form=form) 