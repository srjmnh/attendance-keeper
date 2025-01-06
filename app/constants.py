from enum import Enum, auto
from typing import Dict, List, Set

# User roles
class UserRole(str, Enum):
    ADMIN = 'admin'
    TEACHER = 'teacher'
    STUDENT = 'student'

# User status
class UserStatus(str, Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    SUSPENDED = 'suspended'
    PENDING = 'pending'

# Attendance status
class AttendanceStatus(str, Enum):
    PRESENT = 'present'
    ABSENT = 'absent'
    LATE = 'late'
    EXCUSED = 'excused'

# Subject status
class SubjectStatus(str, Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    ARCHIVED = 'archived'

# Report types
class ReportType(str, Enum):
    DAILY = 'daily'
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    CUSTOM = 'custom'

# File types
class FileType(str, Enum):
    PDF = 'pdf'
    EXCEL = 'excel'
    CSV = 'csv'

# Notification types
class NotificationType(str, Enum):
    EMAIL = 'email'
    PUSH = 'push'
    SMS = 'sms'

# Cache keys
class CacheKey(str, Enum):
    USER_PROFILE = 'user_profile:{}'
    SUBJECT_DETAILS = 'subject_details:{}'
    ATTENDANCE_STATS = 'attendance_stats:{}'
    DAILY_REPORT = 'daily_report:{}'

# API endpoints
class APIEndpoint:
    # Auth endpoints
    AUTH_LOGIN = '/api/auth/login'
    AUTH_LOGOUT = '/api/auth/logout'
    AUTH_REGISTER = '/api/auth/register'
    AUTH_RESET_PASSWORD = '/api/auth/reset-password'
    AUTH_VERIFY_EMAIL = '/api/auth/verify-email'
    
    # User endpoints
    USER_PROFILE = '/api/users/profile'
    USER_UPDATE = '/api/users/update'
    USER_DELETE = '/api/users/delete'
    USER_LIST = '/api/users/list'
    
    # Subject endpoints
    SUBJECT_CREATE = '/api/subjects/create'
    SUBJECT_UPDATE = '/api/subjects/update'
    SUBJECT_DELETE = '/api/subjects/delete'
    SUBJECT_LIST = '/api/subjects/list'
    
    # Attendance endpoints
    ATTENDANCE_MARK = '/api/attendance/mark'
    ATTENDANCE_UPDATE = '/api/attendance/update'
    ATTENDANCE_DELETE = '/api/attendance/delete'
    ATTENDANCE_LIST = '/api/attendance/list'
    
    # Recognition endpoints
    RECOGNITION_REGISTER = '/api/recognition/register'
    RECOGNITION_VERIFY = '/api/recognition/verify'
    RECOGNITION_UPDATE = '/api/recognition/update'
    
    # Report endpoints
    REPORT_GENERATE = '/api/reports/generate'
    REPORT_DOWNLOAD = '/api/reports/download'
    REPORT_LIST = '/api/reports/list'
    
    # Chat endpoints
    CHAT_SEND = '/api/chat/send'
    CHAT_HISTORY = '/api/chat/history'
    CHAT_CLEAR = '/api/chat/clear'

# Database collections
class DBCollection:
    USERS = 'users'
    SUBJECTS = 'subjects'
    ATTENDANCE = 'attendance'
    REPORTS = 'reports'
    CHAT_HISTORY = 'chat_history'
    NOTIFICATIONS = 'notifications'

# Time constants
class TimeConstants:
    SECONDS_IN_MINUTE = 60
    MINUTES_IN_HOUR = 60
    HOURS_IN_DAY = 24
    DAYS_IN_WEEK = 7
    DAYS_IN_MONTH = 30  # Average
    MONTHS_IN_YEAR = 12

# File size limits (in bytes)
class FileSizeLimit:
    PROFILE_PHOTO = 5 * 1024 * 1024  # 5MB
    DOCUMENT = 10 * 1024 * 1024  # 10MB
    REPORT = 20 * 1024 * 1024  # 20MB

# Image dimensions
class ImageDimensions:
    PROFILE_PHOTO_MAX = (800, 800)
    PROFILE_PHOTO_MIN = (100, 100)
    FACE_PHOTO_MAX = (1920, 1080)
    FACE_PHOTO_MIN = (640, 480)

# Rate limiting
class RateLimit:
    LOGIN_ATTEMPTS = 5
    LOGIN_WINDOW = 300  # 5 minutes
    API_REQUESTS = 100
    API_WINDOW = 60  # 1 minute

# Security constants
class SecurityConstants:
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 128
    TOKEN_EXPIRY = 3600  # 1 hour
    REFRESH_TOKEN_EXPIRY = 2592000  # 30 days
    RESET_TOKEN_EXPIRY = 1800  # 30 minutes
    VERIFICATION_CODE_LENGTH = 6
    SESSION_TIMEOUT = 1800  # 30 minutes

# Error messages
class ErrorMessage:
    INVALID_CREDENTIALS = "Invalid email or password"
    ACCOUNT_LOCKED = "Account has been locked due to too many failed attempts"
    ACCOUNT_INACTIVE = "Account is inactive"
    INVALID_TOKEN = "Invalid or expired token"
    PERMISSION_DENIED = "You do not have permission to perform this action"
    RESOURCE_NOT_FOUND = "The requested resource was not found"
    INVALID_REQUEST = "Invalid request parameters"
    SERVER_ERROR = "An unexpected error occurred"
    MAINTENANCE_MODE = "System is currently under maintenance"

# Success messages
class SuccessMessage:
    LOGIN_SUCCESS = "Successfully logged in"
    LOGOUT_SUCCESS = "Successfully logged out"
    REGISTRATION_SUCCESS = "Registration successful"
    PASSWORD_RESET = "Password has been reset successfully"
    PROFILE_UPDATE = "Profile updated successfully"
    ATTENDANCE_MARKED = "Attendance marked successfully"
    REPORT_GENERATED = "Report generated successfully"

# Validation patterns
class ValidationPattern:
    EMAIL = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    PHONE = r'^\+?1?\d{9,15}$'
    USERNAME = r'^[a-zA-Z0-9_-]{3,20}$'
    PASSWORD = r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$'

# Default values
class DefaultValue:
    ITEMS_PER_PAGE = 20
    MAX_ITEMS_PER_PAGE = 100
    CACHE_TIMEOUT = 300  # 5 minutes
    SESSION_LIFETIME = 86400  # 24 hours
    ATTENDANCE_WINDOW = 900  # 15 minutes
    LATE_THRESHOLD = 300  # 5 minutes
    MIN_ATTENDANCE = 75  # Minimum attendance percentage
    MAX_FILE_UPLOADS = 5
    MAX_CHAT_HISTORY = 100

# Feature flags
class FeatureFlag:
    ENABLE_REGISTRATION = True
    ENABLE_PASSWORD_RESET = True
    ENABLE_EMAIL_VERIFICATION = True
    ENABLE_TWO_FACTOR = False
    ENABLE_SOCIAL_LOGIN = False
    ENABLE_API_ACCESS = True
    ENABLE_REPORTS = True
    ENABLE_NOTIFICATIONS = True
    MAINTENANCE_MODE = False

# Supported languages
SUPPORTED_LANGUAGES: Dict[str, str] = {
    'en': 'English',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'hi': 'Hindi',
    'zh': 'Chinese',
    'ja': 'Japanese',
    'ko': 'Korean'
}

# Supported timezones
SUPPORTED_TIMEZONES: Set[str] = {
    'UTC',
    'America/New_York',
    'America/Los_Angeles',
    'Europe/London',
    'Europe/Paris',
    'Asia/Tokyo',
    'Asia/Dubai',
    'Australia/Sydney',
    'Pacific/Auckland'
}

# File extensions
ALLOWED_IMAGE_EXTENSIONS: Set[str] = {'png', 'jpg', 'jpeg', 'gif'}
ALLOWED_DOCUMENT_EXTENSIONS: Set[str] = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv'}
ALLOWED_REPORT_FORMATS: Set[str] = {'pdf', 'xlsx', 'csv'} 