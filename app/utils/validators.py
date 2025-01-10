"""Request validation utilities for the application."""
from functools import wraps
from flask import request, jsonify
from marshmallow import Schema, fields, ValidationError
import bleach
import re
from datetime import datetime

class BaseSchema(Schema):
    """Base schema with common validation methods."""
    
    @staticmethod
    def validate_string_length(value, min_length=1, max_length=255):
        """Validate string length."""
        if not min_length <= len(value) <= max_length:
            raise ValidationError(
                f'Length must be between {min_length} and {max_length} characters'
            )
    
    @staticmethod
    def validate_email(value):
        """Validate email format."""
        email_regex = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_regex.match(value):
            raise ValidationError('Invalid email format')

class UserSchema(BaseSchema):
    """Schema for user data validation."""
    
    email = fields.Email(required=True)
    name = fields.Str(required=True, validate=lambda x: BaseSchema.validate_string_length(x, 2, 50))
    role = fields.Str(required=True, validate=lambda x: x in ['admin', 'teacher', 'student'])
    password = fields.Str(required=True, validate=lambda x: BaseSchema.validate_string_length(x, 8, 128))

class AttendanceSchema(BaseSchema):
    """Schema for attendance data validation."""
    
    student_id = fields.Str(required=True)
    subject_id = fields.Str(required=True)
    date = fields.Date(required=True)
    status = fields.Str(validate=lambda x: x in ['present', 'absent', 'late'])

def validate_request(schema_cls):
    """Decorator to validate request data against a schema."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            schema = schema_cls()
            try:
                # Get request data based on content type
                if request.is_json:
                    data = request.get_json()
                else:
                    data = request.form.to_dict()
                
                # Validate data against schema
                validated_data = schema.load(data)
                
                # Add validated data to request
                request.validated_data = validated_data
                
                return f(*args, **kwargs)
            except ValidationError as err:
                return jsonify({'errors': err.messages}), 400
        return decorated_function
    return decorator

def sanitize_input(text):
    """Sanitize input text to prevent XSS."""
    return bleach.clean(
        text,
        tags=['b', 'i', 'u', 'em', 'strong'],
        attributes={},
        strip=True
    )

def validate_date_range(start_date, end_date):
    """Validate date range."""
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        if start > end:
            raise ValidationError('Start date must be before end date')
        return start, end
    except ValueError:
        raise ValidationError('Invalid date format. Use YYYY-MM-DD')

def validate_file_upload(file, allowed_extensions=None, max_size_mb=16):
    """Validate file upload."""
    if not file:
        raise ValidationError('No file provided')
    
    if allowed_extensions is None:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    
    # Check filename
    filename = file.filename
    if not filename or '.' not in filename:
        raise ValidationError('Invalid filename')
    
    # Check extension
    ext = filename.rsplit('.', 1)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}')
    
    # Check file size
    file.seek(0, 2)  # Seek to end of file
    size_mb = file.tell() / (1024 * 1024)  # Convert to MB
    file.seek(0)  # Reset file pointer
    
    if size_mb > max_size_mb:
        raise ValidationError(f'File size exceeds maximum limit of {max_size_mb}MB')
    
    # Check if file is actually an image
    if ext in {'png', 'jpg', 'jpeg', 'gif'}:
        try:
            from PIL import Image
            img = Image.open(file)
            img.verify()  # Verify it's actually an image
            file.seek(0)  # Reset file pointer after verification
        except Exception:
            raise ValidationError('Invalid image file')
    
    return True

def validate_image_dimensions(image, min_width=100, min_height=100, max_width=4096, max_height=4096):
    """Validate image dimensions."""
    from PIL import Image
    
    try:
        # If image is a file object, seek to start
        if hasattr(image, 'seek'):
            image.seek(0)
        
        img = Image.open(image)
        width, height = img.size
        
        if not (min_width <= width <= max_width and min_height <= height <= max_height):
            raise ValidationError(
                f'Image dimensions must be between {min_width}x{min_height} and {max_width}x{max_height}'
            )
        
        # Check image format
        if img.format.lower() not in {'png', 'jpeg', 'gif'}:
            raise ValidationError('Unsupported image format')
        
        # Check color mode
        if img.mode not in {'RGB', 'RGBA', 'L'}:
            raise ValidationError('Unsupported color mode')
        
        # Reset file pointer if it's a file object
        if hasattr(image, 'seek'):
            image.seek(0)
        
        return True
    except Exception as e:
        raise ValidationError(f'Invalid image: {str(e)}') 