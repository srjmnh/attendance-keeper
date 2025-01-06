"""
Services Package
--------------

This package contains the service classes that handle
business logic and external service integrations.

Services:
- FaceService: AWS Rekognition integration for facial recognition
- DatabaseService: Firebase Firestore integration for data storage
- AIService: Gemini AI integration for insights and chat
"""

from .face_service import FaceService
from .db_service import DatabaseService
from .ai_service import AIService

__all__ = ['FaceService', 'DatabaseService', 'AIService'] 