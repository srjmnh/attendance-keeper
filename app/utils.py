import os
import re
import uuid
import pytz
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from PIL import Image
from werkzeug.utils import secure_filename
from flask import current_app, url_for
import jwt
from functools import wraps
from flask_login import current_user
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

def allowed_file(filename: str) -> bool:
    """Check if a file has an allowed extension"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_image(image_file, folder: str = 'uploads') -> Optional[str]:
    """Save an image file and return its filename"""
    try:
        if not image_file:
            return None
        
        # Generate a secure filename with UUID
        filename = secure_filename(image_file.filename)
        ext = filename.rsplit('.', 1)[1].lower()
        new_filename = f"{uuid.uuid4().hex}.{ext}"
        
        # Create folder if it doesn't exist
        folder_path = os.path.join(current_app.config['UPLOAD_FOLDER'], folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        # Save and optimize image
        filepath = os.path.join(folder_path, new_filename)
        with Image.open(image_file) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if too large
            max_size = 1920
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size))
            
            # Save with optimization
            img.save(filepath, 'JPEG', quality=85, optimize=True)
        
        return new_filename
    except Exception as e:
        logger.error(f"Error saving image: {str(e)}")
        return None

def delete_file(filename: str, folder: str = 'uploads') -> bool:
    """Delete a file from the specified folder"""
    try:
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], folder, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return False

def get_file_url(filename: str, folder: str = 'uploads') -> Optional[str]:
    """Get the URL for a file"""
    if not filename:
        return None
    return url_for('static', filename=f'{folder}/{filename}', _external=True)

def generate_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate a JWT token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    data.update({'exp': expire})
    return jwt.encode(data, current_app.config['SECRET_KEY'], algorithm='HS256')

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify a JWT token and return its payload"""
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError:
        logger.warning("Invalid token")
        return None

def format_datetime(dt: datetime, timezone: str = 'UTC', format: str = '%Y-%m-%d %H:%M:%S') -> str:
    """Format a datetime object with timezone support"""
    if not dt.tzinfo:
        dt = pytz.UTC.localize(dt)
    tz = pytz.timezone(timezone)
    return dt.astimezone(tz).strftime(format)

def parse_datetime(date_str: str, timezone: str = 'UTC') -> Optional[datetime]:
    """Parse a datetime string with timezone support"""
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        tz = pytz.timezone(timezone)
        return tz.localize(dt)
    except ValueError:
        return None

def is_valid_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def is_strong_password(password: str) -> tuple[bool, str]:
    """
    Check if a password is strong enough.
    Returns a tuple of (is_valid, message).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, "Password is strong"

def hash_password(password: str) -> str:
    """Generate a secure hash of the password"""
    return generate_password_hash(password, method='pbkdf2:sha256:100000')

def generate_unique_filename(filename: str) -> str:
    """Generate a unique filename using UUID"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return f"{uuid.uuid4().hex}.{ext}"

def calculate_attendance_percentage(present: int, total: int) -> float:
    """Calculate attendance percentage"""
    if total == 0:
        return 0.0
    return round((present / total) * 100, 2)

def requires_roles(*roles):
    """Decorator to restrict access based on user roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return current_app.login_manager.unauthorized()
            if not current_user.role in roles:
                return current_app.login_manager.unauthorized()
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def paginate(items: List[Any], page: int = 1, per_page: int = 10) -> Dict[str, Any]:
    """Helper function for pagination"""
    total = len(items)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    return {
        'items': items[start_idx:end_idx],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
        'has_prev': page > 1,
        'has_next': end_idx < total
    }

def format_file_size(size: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to make it safe for all operating systems"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Remove control characters
    filename = "".join(char for char in filename if ord(char) >= 32)
    return secure_filename(filename)

def generate_report_filename(report_type: str, extension: str) -> str:
    """Generate a filename for reports"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"attendance_report_{report_type}_{timestamp}.{extension}"

def format_phone_number(phone: str) -> Optional[str]:
    """Format phone number to a standard format"""
    if not phone:
        return None
    # Remove all non-numeric characters
    numbers = re.sub(r'\D', '', phone)
    if len(numbers) == 10:
        return f"+1 ({numbers[:3]}) {numbers[3:6]}-{numbers[6:]}"
    elif len(numbers) == 11 and numbers[0] == '1':
        return f"+{numbers[0]} ({numbers[1:4]}) {numbers[4:7]}-{numbers[7:]}"
    return None

def get_gravatar_url(email: str, size: int = 80) -> str:
    """Get Gravatar URL for an email address"""
    email_hash = hashlib.md5(email.lower().encode('utf-8')).hexdigest()
    return f"https://www.gravatar.com/avatar/{email_hash}?s={size}&d=identicon"

def format_timedelta(td: timedelta) -> str:
    """Format a timedelta object into a human-readable string"""
    days = td.days
    hours = td.seconds // 3600
    minutes = (td.seconds % 3600) // 60
    
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    
    return " ".join(parts) if parts else "0m"

def truncate_string(text: str, length: int = 100, suffix: str = '...') -> str:
    """Truncate a string to a specified length"""
    if len(text) <= length:
        return text
    return text[:length].rsplit(' ', 1)[0] + suffix

def is_valid_uuid(val: str) -> bool:
    """Check if a string is a valid UUID"""
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False

def normalize_email(email: str) -> str:
    """Normalize an email address"""
    email = email.strip().lower()
    local, domain = email.split('@')
    # Remove dots and anything after + in local part
    local = local.split('+')[0].replace('.', '')
    return f"{local}@{domain}" 