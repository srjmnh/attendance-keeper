from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from jose import jwt

from ..models.user import User
from .. import db_service

bp = Blueprint('auth', __name__, url_prefix='/auth')

def generate_token(user_id: str, expires_delta: timedelta = None) -> str:
    """Generate JWT token for user"""
    if expires_delta is None:
        expires_delta = timedelta(days=1)
    
    expires = datetime.utcnow() + expires_delta
    
    to_encode = {
        'exp': expires,
        'iat': datetime.utcnow(),
        'sub': user_id
    }
    
    return jwt.encode(
        to_encode,
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )

@bp.route('/login', methods=['POST'])
def login():
    """Login user and return access token"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        username = data.get('username')
        password = data.get('password')
        remember = data.get('remember', False)

        if not username or not password:
            return jsonify({
                'error': 'Missing required fields: username, password'
            }), 400

        # Get user
        user = User.get_by_username(username)
        if not user:
            return jsonify({'error': 'Invalid username or password'}), 401

        # Check password
        if not check_password_hash(user.password_hash, password):
            return jsonify({'error': 'Invalid username or password'}), 401

        # Check if user is active
        if not user.active:
            return jsonify({'error': 'Account is inactive'}), 401

        # Login user
        login_user(user, remember=remember)

        # Generate access token
        token = generate_token(user.id)

        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': user.to_dict()
        })

    except Exception as e:
        current_app.logger.error(f"Error logging in: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout current user"""
    try:
        logout_user()
        return jsonify({'message': 'Logout successful'})

    except Exception as e:
        current_app.logger.error(f"Error logging out: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/token/refresh', methods=['POST'])
@login_required
def refresh_token():
    """Refresh access token"""
    try:
        token = generate_token(current_user.id)
        return jsonify({
            'message': 'Token refreshed successfully',
            'token': token
        })

    except Exception as e:
        current_app.logger.error(f"Error refreshing token: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/password/change', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        current_password = data.get('current_password')
        new_password = data.get('new_password')

        if not current_password or not new_password:
            return jsonify({
                'error': 'Missing required fields: current_password, new_password'
            }), 400

        # Check current password
        if not check_password_hash(current_user.password_hash, current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401

        # Update password
        password_hash = generate_password_hash(new_password)
        if not current_user.update({'password': password_hash}):
            return jsonify({'error': 'Failed to update password'}), 500

        return jsonify({'message': 'Password updated successfully'})

    except Exception as e:
        current_app.logger.error(f"Error changing password: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/password/reset/request', methods=['POST'])
def request_password_reset():
    """Request password reset"""
    try:
        data = request.get_json()
        if not data or 'username' not in data:
            return jsonify({'error': 'Username is required'}), 400

        # Get user
        user = User.get_by_username(data['username'])
        if not user:
            # Return success even if user doesn't exist (security)
            return jsonify({
                'message': 'If the username exists, a reset link will be sent'
            })

        # Generate reset token (24 hour expiry)
        token = generate_token(user.id, expires_delta=timedelta(hours=24))

        # Send reset email (implement email sending logic)
        reset_link = f"{request.host_url}reset-password?token={token}"
        # TODO: Implement email sending

        return jsonify({
            'message': 'If the username exists, a reset link will be sent'
        })

    except Exception as e:
        current_app.logger.error(f"Error requesting password reset: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/password/reset/verify', methods=['POST'])
def verify_reset_token():
    """Verify password reset token"""
    try:
        data = request.get_json()
        if not data or 'token' not in data:
            return jsonify({'error': 'Reset token is required'}), 400

        try:
            payload = jwt.decode(
                data['token'],
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            user_id = payload['sub']
        except jwt.JWTError:
            return jsonify({'error': 'Invalid or expired reset token'}), 401

        # Check if user exists
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({'message': 'Reset token is valid'})

    except Exception as e:
        current_app.logger.error(f"Error verifying reset token: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/password/reset', methods=['POST'])
def reset_password():
    """Reset password using token"""
    try:
        data = request.get_json()
        if not data or 'token' not in data or 'new_password' not in data:
            return jsonify({
                'error': 'Reset token and new password are required'
            }), 400

        try:
            payload = jwt.decode(
                data['token'],
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            user_id = payload['sub']
        except jwt.JWTError:
            return jsonify({'error': 'Invalid or expired reset token'}), 401

        # Get user
        user = User.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Update password
        password_hash = generate_password_hash(data['new_password'])
        if not user.update({'password': password_hash}):
            return jsonify({'error': 'Failed to reset password'}), 500

        return jsonify({'message': 'Password reset successfully'})

    except Exception as e:
        current_app.logger.error(f"Error resetting password: {str(e)}")
        return jsonify({'error': str(e)}), 500 