from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.services.db_service import DatabaseService
from app.models.user import User
import re

auth = Blueprint('auth', __name__)
db = DatabaseService()

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = db.get_user_by_email(email)
        
        if not user or not check_password_hash(user.password, password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('auth.login'))
        
        if user.status != 'active':
            flash('Your account is not active. Please contact the administrator.', 'warning')
            return redirect(url_for('auth.login'))
        
        login_user(User.from_dict(user), remember=remember)
        return redirect(url_for('main.index'))
    
    return render_template('auth/login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handle user registration.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
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
            return redirect(url_for('auth.register'))
        
        # Check if email already exists
        if db.get_user_by_email(email):
            flash('Email address already exists.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Validate password strength
        if not re.match(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$", password):
            flash('Password must be at least 8 characters long and contain letters and numbers.', 'danger')
            return redirect(url_for('auth.register'))
        
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
                flash('Please select your class and division.', 'danger')
                return redirect(url_for('auth.register'))
            user['class_name'] = class_name
            user['division'] = division
        
        # Save user to database
        try:
            user_id = db.create_user(user)
            if user_id:
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('auth.login'))
        except Exception as e:
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('auth.register'))
    
    return render_template('auth/register.html')

@auth.route('/logout')
@login_required
def logout():
    """
    Handle user logout.
    """
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """
    Handle password reset request.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('Please enter your email address.', 'danger')
            return redirect(url_for('auth.reset_password'))
        
        user = db.get_user_by_email(email)
        if not user:
            flash('No account found with that email address.', 'danger')
            return redirect(url_for('auth.reset_password'))
        
        # Generate password reset token and send email
        try:
            token = generate_reset_token()
            db.save_reset_token(email, token)
            send_reset_email(email, token)
            flash('Password reset instructions have been sent to your email.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash('An error occurred. Please try again.', 'danger')
            return redirect(url_for('auth.reset_password'))
    
    return render_template('auth/reset_password.html')

@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_confirm(token):
    """
    Handle password reset confirmation.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    # Verify token
    email = db.verify_reset_token(token)
    if not email:
        flash('Invalid or expired reset token.', 'danger')
        return redirect(url_for('auth.reset_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.reset_password_confirm', token=token))
        
        # Validate password strength
        if not re.match(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$", password):
            flash('Password must be at least 8 characters long and contain letters and numbers.', 'danger')
            return redirect(url_for('auth.reset_password_confirm', token=token))
        
        try:
            db.update_user_password(email, generate_password_hash(password))
            db.delete_reset_token(token)
            flash('Your password has been updated! Please login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash('An error occurred. Please try again.', 'danger')
            return redirect(url_for('auth.reset_password_confirm', token=token))
    
    return render_template('auth/reset_password_confirm.html')

@auth.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    Handle user profile management.
    """
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        
        # Update user details
        try:
            user = db.get_user_by_id(current_user.id)
            
            # Update name
            if first_name and last_name:
                db.update_user(current_user.id, {
                    'first_name': first_name,
                    'last_name': last_name
                })
                flash('Profile updated successfully.', 'success')
            
            # Update password
            if current_password and new_password:
                if not check_password_hash(user.password, current_password):
                    flash('Current password is incorrect.', 'danger')
                    return redirect(url_for('auth.profile'))
                
                if not re.match(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$", new_password):
                    flash('New password must be at least 8 characters long and contain letters and numbers.', 'danger')
                    return redirect(url_for('auth.profile'))
                
                db.update_user_password(user.email, generate_password_hash(new_password))
                flash('Password updated successfully.', 'success')
            
            return redirect(url_for('auth.profile'))
        except Exception as e:
            flash('An error occurred. Please try again.', 'danger')
            return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html')

def generate_reset_token():
    """
    Generate a secure token for password reset.
    """
    import secrets
    return secrets.token_urlsafe(32)

def send_reset_email(email, token):
    """
    Send password reset email to user.
    """
    # TODO: Implement email sending functionality
    pass 