from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.services.db_service import DatabaseService
from app.models.user import User
from datetime import datetime
import logging
import re

auth = Blueprint('auth', __name__)
db = DatabaseService()
logger = logging.getLogger(__name__)

def validate_password(password):
    """
    Validate password strength
    - At least 8 characters long
    - Contains at least one letter and one number
    - Can contain special characters
    """
    if len(password) < 8:
        return False
    if not re.search(r"[A-Za-z]", password):  # At least one letter
        return False
    if not re.search(r"\d", password):  # At least one number
        return False
    return True

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            remember = True if request.form.get('remember') else False
            
            logger.info(f"Login attempt for email: {email}")
            
            if not email or not password:
                logger.warning("Missing email or password")
                flash('Please enter both email and password.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Get user from database
            user_dict = db.get_user_by_email(email)
            logger.info(f"User lookup result: {user_dict}")
            
            if not user_dict:
                logger.warning(f"No user found for email: {email}")
                flash('Please check your login details and try again.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Create User object from dictionary
            user = User(user_dict)
            logger.info(f"User object created with role: {user.role}")
            
            # Check password using the password_hash from user object
            if not user.check_password(password):
                logger.warning(f"Invalid password for user: {email}")
                flash('Please check your login details and try again.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Check if user is active
            if user_dict.get('status') != 'active':
                logger.warning(f"Inactive user attempted login: {email}")
                flash('Your account is not active. Please contact the administrator.', 'warning')
                return redirect(url_for('auth.login'))
            
            login_user(user, remember=remember)
            logger.info(f"User {email} logged in successfully")
            
            # Redirect to next page if specified, otherwise go to index
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            logger.exception("Full traceback:")
            flash('An error occurred during login. Please try again.', 'danger')
            return redirect(url_for('auth.login'))
    
    return render_template('auth/login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """
    Handle user registration.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        try:
            email = request.form.get('email')
            password = request.form.get('password')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            role = request.form.get('role')
            class_name = request.form.get('class_name')
            division = request.form.get('division')
            
            # Validate required fields
            if not all([email, password, first_name, last_name, role]):
                flash('Please fill in all required fields.', 'danger')
                return redirect(url_for('auth.register'))
            
            # Validate email format
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                flash('Please enter a valid email address.', 'danger')
                return redirect(url_for('auth.register'))
            
            # Check if email already exists
            if db.get_user_by_email(email):
                flash('Email address already exists.', 'danger')
                return redirect(url_for('auth.register'))
            
            # Validate password strength
            if not validate_password(password):
                flash('Password must be at least 8 characters long and contain both letters and numbers.', 'danger')
                return redirect(url_for('auth.register'))
            
            # Create user data
            user_data = {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'role': role,
                'status': 'active',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Add class and division for students
            if role == 'student':
                if not class_name or not division:
                    flash('Please select your class and division.', 'danger')
                    return redirect(url_for('auth.register'))
                user_data['class_name'] = class_name
                user_data['division'] = division
            
            # Create User object and set password
            user = User(user_data)
            user.set_password(password)
            
            # Save user to database
            db.create_user(user.to_dict())
            logger.info(f"User registered successfully: {email}")
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
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

@auth.route('/create-admin')
def create_admin():
    """Create default admin account if it doesn't exist"""
    try:
        email = "admin@attendance.com"
        password = "Admin@123"
        
        logger.info("Attempting to create admin account...")
        
        # Check if admin already exists
        existing_admin = db.get_user_by_email(email)
        logger.info(f"Existing admin check result: {existing_admin}")
        
        if existing_admin:
            logger.info("Admin account already exists")
            flash('Admin account already exists. Please login.', 'info')
            return redirect(url_for('auth.login'))
        
        # Create admin user data
        admin_data = {
            'email': email,
            'first_name': 'System',
            'last_name': 'Admin',
            'role': 'admin',
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        logger.info(f"Admin data prepared: {admin_data}")
        
        # Create User object and set password
        admin = User(admin_data)
        admin.set_password(password)
        logger.info("Password set for admin user")
        
        # Convert to dictionary for database storage
        admin_dict = admin.to_dict()
        logger.info(f"Admin dictionary created: {admin_dict}")
        
        # Save to database
        result = db.create_user(admin_dict)
        logger.info(f"Admin user creation result: {result}")
        
        flash('Admin account created successfully! Email: admin@attendance.com, Password: Admin@123', 'success')
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        logger.error(f"Error creating admin user: {str(e)}")
        logger.exception("Full traceback:")
        flash('Error creating admin account. Please try again.', 'danger')
        return redirect(url_for('auth.login')) 

@auth.route('/setup-admin')
def setup_admin():
    """Create the default admin account"""
    try:
        email = "admin@attendance.com"
        password = "Admin@123"
        
        logger.info("Checking for existing admin account...")
        existing_admin = db.get_user_by_email(email)
        
        if existing_admin:
            logger.info("Admin account already exists")
            flash('Admin account already exists. Please login with admin@attendance.com', 'info')
            return redirect(url_for('auth.login'))
        
        # Create admin user data
        admin_data = {
            'email': email,
            'first_name': 'System',
            'last_name': 'Admin',
            'role': 'admin',
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Create User object and set password
        admin = User(admin_data)
        admin.set_password(password)
        
        # Save to database
        db.create_user(admin.to_dict())
        
        logger.info("Admin account created successfully")
        flash('Admin account created! Please login with admin@attendance.com / Admin@123', 'success')
        return redirect(url_for('auth.login'))
        
    except Exception as e:
        logger.error(f"Error creating admin account: {str(e)}")
        flash('Error creating admin account. Please try again.', 'danger')
        return redirect(url_for('auth.login')) 