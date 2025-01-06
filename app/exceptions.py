from typing import Optional, Dict, Any
from werkzeug.exceptions import HTTPException

class AttendanceError(Exception):
    """Base exception class for attendance system"""
    def __init__(self, message: str, status_code: int = 500, payload: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format"""
        error_dict = dict(self.payload or ())
        error_dict['message'] = self.message
        error_dict['status_code'] = self.status_code
        return error_dict

class ValidationError(AttendanceError):
    """Exception raised for validation errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, payload=payload)

class AuthenticationError(AttendanceError):
    """Exception raised for authentication errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=401, payload=payload)

class AuthorizationError(AttendanceError):
    """Exception raised for authorization errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=403, payload=payload)

class ResourceNotFoundError(AttendanceError):
    """Exception raised when a resource is not found"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=404, payload=payload)

class ResourceConflictError(AttendanceError):
    """Exception raised when there is a conflict with existing resources"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=409, payload=payload)

class RateLimitExceededError(AttendanceError):
    """Exception raised when rate limit is exceeded"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=429, payload=payload)

class ServiceUnavailableError(AttendanceError):
    """Exception raised when a service is unavailable"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=503, payload=payload)

class DatabaseError(AttendanceError):
    """Exception raised for database errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, payload=payload)

class FaceRecognitionError(AttendanceError):
    """Exception raised for face recognition errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, payload=payload)

class AIServiceError(AttendanceError):
    """Exception raised for AI service errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, payload=payload)

class FileUploadError(AttendanceError):
    """Exception raised for file upload errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, payload=payload)

class InvalidTokenError(AttendanceError):
    """Exception raised for invalid token errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=401, payload=payload)

class ExpiredTokenError(AttendanceError):
    """Exception raised for expired token errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=401, payload=payload)

class ConfigurationError(AttendanceError):
    """Exception raised for configuration errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, payload=payload)

class ThirdPartyServiceError(AttendanceError):
    """Exception raised for third-party service errors"""
    def __init__(self, message: str, service_name: str, payload: Optional[Dict[str, Any]] = None):
        payload = payload or {}
        payload['service_name'] = service_name
        super().__init__(message, status_code=503, payload=payload)

class InvalidRequestError(AttendanceError):
    """Exception raised for invalid request errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, payload=payload)

class BusinessLogicError(AttendanceError):
    """Exception raised for business logic errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=422, payload=payload)

class AttendanceRecordError(AttendanceError):
    """Exception raised for attendance record errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, payload=payload)

class UserError(AttendanceError):
    """Exception raised for user-related errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, payload=payload)

class SubjectError(AttendanceError):
    """Exception raised for subject-related errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, payload=payload)

class ReportGenerationError(AttendanceError):
    """Exception raised for report generation errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, payload=payload)

class NotificationError(AttendanceError):
    """Exception raised for notification errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, payload=payload)

class CacheError(AttendanceError):
    """Exception raised for cache-related errors"""
    def __init__(self, message: str, payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, payload=payload)

class BackgroundTaskError(AttendanceError):
    """Exception raised for background task errors"""
    def __init__(self, message: str, task_id: str, payload: Optional[Dict[str, Any]] = None):
        payload = payload or {}
        payload['task_id'] = task_id
        super().__init__(message, status_code=500, payload=payload)

class MaintenanceModeError(AttendanceError):
    """Exception raised when system is in maintenance mode"""
    def __init__(self, message: str = "System is under maintenance", payload: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=503, payload=payload) 