from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from ..models.user import User
from ..forms.auth import LoginForm, RegistrationForm
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('index.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        try:
            user = User.get_by_username(form.username.data)
            if user and check_password_hash(user.password_hash, form.password.data):
                login_user(user)
                flash('Login successful!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page if next_page else url_for('index.dashboard'))
            else:
                flash('Invalid username or password', 'error')
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login', 'error')

    return render_template('auth/login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('auth.login'))

@bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    """Handle user registration (admin only)"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index.dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # Check if username already exists
            if User.get_by_username(form.username.data):
                flash('Username already exists', 'error')
                return render_template('auth/register.html', form=form)

            # Create new user
            user = User.create(
                username=form.username.data,
                password_hash=generate_password_hash(form.password.data),
                email=form.email.data,
                role=form.role.data,
                name=form.name.data
            )

            flash(f'User {user.username} registered successfully', 'success')
            return redirect(url_for('admin.manage_users'))

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration', 'error')

    return render_template('auth/register.html', form=form)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Handle user profile updates"""
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Update email
            if 'email' in data:
                current_user.update_email(data['email'])
            
            # Update password
            if 'current_password' in data and 'new_password' in data:
                if not check_password_hash(current_user.password_hash, data['current_password']):
                    return jsonify({'error': 'Current password is incorrect'}), 400
                
                current_user.update_password(
                    generate_password_hash(data['new_password'])
                )
            
            return jsonify({'message': 'Profile updated successfully'})
        
        except Exception as e:
            logger.error(f"Profile update error: {str(e)}")
            return jsonify({'error': 'An error occurred updating profile'}), 500

    return render_template('auth/profile.html') 