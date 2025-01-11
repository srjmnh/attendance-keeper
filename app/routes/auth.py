from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, current_user
from app.services.db_service import DatabaseService
from app.models.user import User
from app.forms.auth import LoginForm
from werkzeug.security import check_password_hash

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