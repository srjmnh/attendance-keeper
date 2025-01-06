from marshmallow import Schema, fields, validate, validates, ValidationError, EXCLUDE
from datetime import datetime
from typing import Optional, List, Dict, Any
from .constants import (
    UserRole, UserStatus, AttendanceStatus, SubjectStatus,
    ReportType, NotificationType, ValidationPattern
)

class BaseSchema(Schema):
    """Base schema with common configuration"""
    class Meta:
        unknown = EXCLUDE
        ordered = True

class UserSchema(BaseSchema):
    """Schema for user data"""
    id = fields.String(dump_only=True)
    email = fields.Email(required=True, validate=validate.Regexp(ValidationPattern.EMAIL))
    password = fields.String(
        load_only=True,
        validate=validate.Regexp(ValidationPattern.PASSWORD),
        required=True
    )
    first_name = fields.String(required=True, validate=validate.Length(min=2, max=50))
    last_name = fields.String(required=True, validate=validate.Length(min=2, max=50))
    role = fields.String(
        required=True,
        validate=validate.OneOf([role.value for role in UserRole])
    )
    status = fields.String(
        dump_only=True,
        validate=validate.OneOf([status.value for status in UserStatus])
    )
    phone = fields.String(validate=validate.Regexp(ValidationPattern.PHONE))
    profile_photo = fields.String(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    last_login = fields.DateTime(dump_only=True)

class LoginSchema(BaseSchema):
    """Schema for login data"""
    email = fields.Email(required=True)
    password = fields.String(required=True, load_only=True)
    remember_me = fields.Boolean(missing=False)

class RegistrationSchema(UserSchema):
    """Schema for user registration"""
    confirm_password = fields.String(required=True, load_only=True)
    
    @validates('confirm_password')
    def validate_confirm_password(self, value):
        if value != self.context.get('password'):
            raise ValidationError('Passwords do not match')

class PasswordResetRequestSchema(BaseSchema):
    """Schema for password reset request"""
    email = fields.Email(required=True)

class PasswordResetSchema(BaseSchema):
    """Schema for password reset"""
    token = fields.String(required=True)
    password = fields.String(
        required=True,
        validate=validate.Regexp(ValidationPattern.PASSWORD)
    )
    confirm_password = fields.String(required=True)
    
    @validates('confirm_password')
    def validate_confirm_password(self, value):
        if value != self.context.get('password'):
            raise ValidationError('Passwords do not match')

class SubjectSchema(BaseSchema):
    """Schema for subject data"""
    id = fields.String(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(min=2, max=100))
    code = fields.String(required=True, validate=validate.Length(min=2, max=20))
    description = fields.String(validate=validate.Length(max=500))
    teacher_id = fields.String(required=True)
    status = fields.String(
        validate=validate.OneOf([status.value for status in SubjectStatus])
    )
    schedule = fields.Dict(keys=fields.String(), values=fields.List(fields.String()))
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

class AttendanceSchema(BaseSchema):
    """Schema for attendance data"""
    id = fields.String(dump_only=True)
    student_id = fields.String(required=True)
    subject_id = fields.String(required=True)
    date = fields.Date(required=True)
    status = fields.String(
        required=True,
        validate=validate.OneOf([status.value for status in AttendanceStatus])
    )
    time_in = fields.DateTime()
    time_out = fields.DateTime()
    remarks = fields.String(validate=validate.Length(max=200))
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    @validates('time_out')
    def validate_time_out(self, value):
        if value and self.context.get('time_in'):
            if value <= self.context['time_in']:
                raise ValidationError('Time out must be after time in')

class FaceRecognitionSchema(BaseSchema):
    """Schema for face recognition data"""
    student_id = fields.String(required=True)
    image = fields.String(required=True)  # Base64 encoded image
    confidence_score = fields.Float(dump_only=True)
    face_id = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

class ReportSchema(BaseSchema):
    """Schema for report generation"""
    report_type = fields.String(
        required=True,
        validate=validate.OneOf([type.value for type in ReportType])
    )
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    subject_id = fields.String()
    teacher_id = fields.String()
    student_id = fields.String()
    format = fields.String(
        required=True,
        validate=validate.OneOf(['pdf', 'excel', 'csv'])
    )
    
    @validates('end_date')
    def validate_date_range(self, value):
        if value < self.context.get('start_date'):
            raise ValidationError('End date must be after start date')

class NotificationSchema(BaseSchema):
    """Schema for notification data"""
    id = fields.String(dump_only=True)
    recipient_id = fields.String(required=True)
    type = fields.String(
        required=True,
        validate=validate.OneOf([type.value for type in NotificationType])
    )
    title = fields.String(required=True, validate=validate.Length(min=1, max=100))
    message = fields.String(required=True, validate=validate.Length(min=1, max=500))
    data = fields.Dict(keys=fields.String(), values=fields.Raw())
    read = fields.Boolean(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

class ChatMessageSchema(BaseSchema):
    """Schema for chat messages"""
    id = fields.String(dump_only=True)
    user_id = fields.String(required=True)
    message = fields.String(required=True, validate=validate.Length(min=1, max=1000))
    response = fields.String(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

class PaginationSchema(BaseSchema):
    """Schema for pagination parameters"""
    page = fields.Integer(missing=1, validate=validate.Range(min=1))
    per_page = fields.Integer(missing=20, validate=validate.Range(min=1, max=100))

class SearchSchema(BaseSchema):
    """Schema for search parameters"""
    query = fields.String(required=True, validate=validate.Length(min=1, max=100))
    filters = fields.Dict(keys=fields.String(), values=fields.Raw())
    sort_by = fields.String()
    sort_order = fields.String(validate=validate.OneOf(['asc', 'desc']))

class ErrorSchema(BaseSchema):
    """Schema for error responses"""
    code = fields.Integer(required=True)
    message = fields.String(required=True)
    details = fields.Dict(keys=fields.String(), values=fields.Raw())

class SuccessSchema(BaseSchema):
    """Schema for success responses"""
    message = fields.String(required=True)
    data = fields.Raw()

class FileUploadSchema(BaseSchema):
    """Schema for file upload"""
    file = fields.Raw(required=True)
    type = fields.String(required=True, validate=validate.OneOf(['image', 'document']))
    description = fields.String(validate=validate.Length(max=200))

class TokenSchema(BaseSchema):
    """Schema for authentication tokens"""
    access_token = fields.String(required=True)
    refresh_token = fields.String(required=True)
    token_type = fields.String(required=True)
    expires_in = fields.Integer(required=True) 