"""
Models Package
-------------

This package contains the data models for the application.
Each model represents a database entity and provides methods
for interacting with the data.

Models:
- User: User account management
- Subject: Subject/class management
- Attendance: Attendance record management
"""

from .user import User
from .subject import Subject
from .attendance import Attendance

__all__ = ['User', 'Subject', 'Attendance'] 