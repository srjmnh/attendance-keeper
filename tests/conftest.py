"""Test configuration and fixtures"""

import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask
from werkzeug.security import generate_password_hash

from app import create_app
from app.models.user import User
from app.services.ai_service import AIService
from app.services.face_service import FaceService
from app.services.db_service import DatabaseService

@pytest.fixture
def app():
    """Create and configure a test Flask application"""
    app = create_app({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'AWS_ACCESS_KEY_ID': 'test-aws-key',
        'AWS_SECRET_ACCESS_KEY': 'test-aws-secret',
        'AWS_REGION': 'us-east-1',
        'AWS_COLLECTION_ID': 'test-collection',
        'FIREBASE_ADMIN_CREDENTIALS_BASE64': 'test-credentials',
        'GEMINI_API_KEY': 'test-gemini-key',
        'GEMINI_MODEL': 'test-model',
        'GEMINI_TEMPERATURE': 0.7,
        'GEMINI_TOP_P': 0.8,
        'GEMINI_TOP_K': 40
    })
    
    return app

@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create a test CLI runner"""
    return app.test_cli_runner()

@pytest.fixture
def mock_db():
    """Mock Firestore database"""
    mock_firestore = Mock(spec=firestore.Client)
    mock_collection = Mock(spec=firestore.CollectionReference)
    mock_doc = Mock(spec=firestore.DocumentReference)
    
    mock_firestore.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_doc
    
    with patch('firebase_admin.firestore.client') as mock_client:
        mock_client.return_value = mock_firestore
        yield mock_firestore

@pytest.fixture
def mock_rekognition():
    """Mock AWS Rekognition client"""
    with patch('boto3.client') as mock_client:
        mock_rekognition = Mock()
        mock_client.return_value = mock_rekognition
        yield mock_rekognition

@pytest.fixture
def mock_gemini():
    """Mock Gemini AI client"""
    with patch('google.generativeai.GenerativeModel') as mock_model:
        mock_gemini = Mock()
        mock_model.return_value = mock_gemini
        yield mock_gemini

@pytest.fixture
def test_user():
    """Create a test user"""
    return {
        'id': 'test-user-id',
        'username': 'testuser',
        'password_hash': generate_password_hash('testpass'),
        'role': 'admin',
        'email': 'test@example.com',
        'created_at': datetime.now(),
        'last_login': datetime.now()
    }

@pytest.fixture
def test_student():
    """Create a test student"""
    return {
        'id': 'test-student-id',
        'name': 'Test Student',
        'email': 'student@example.com',
        'face_id': 'test-face-id',
        'subjects': ['test-subject-1', 'test-subject-2'],
        'created_at': datetime.now()
    }

@pytest.fixture
def test_subject():
    """Create a test subject"""
    return {
        'id': 'test-subject-id',
        'name': 'Test Subject',
        'code': 'TST101',
        'teacher_id': 'test-teacher-id',
        'schedule': {
            'day': 'Monday',
            'time': '09:00'
        },
        'created_at': datetime.now()
    }

@pytest.fixture
def test_attendance():
    """Create test attendance records"""
    return [
        {
            'id': 'test-attendance-1',
            'student_id': 'test-student-id',
            'subject_id': 'test-subject-id',
            'timestamp': datetime.now(),
            'status': 'present',
            'confidence': 98.5
        },
        {
            'id': 'test-attendance-2',
            'student_id': 'test-student-id',
            'subject_id': 'test-subject-id',
            'timestamp': datetime.now() - timedelta(days=1),
            'status': 'absent',
            'confidence': 0.0
        }
    ]

@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers"""
    return {'Authorization': f'Bearer test-token'}

@pytest.fixture
def mock_services(mock_db, mock_rekognition, mock_gemini):
    """Mock all services"""
    with patch('app.services.db_service.DatabaseService') as mock_db_service, \
         patch('app.services.face_service.FaceService') as mock_face_service, \
         patch('app.services.ai_service.AIService') as mock_ai_service:
        
        yield {
            'db_service': mock_db_service,
            'face_service': mock_face_service,
            'ai_service': mock_ai_service
        }

@pytest.fixture
def sample_image():
    """Create a sample image for testing"""
    return {
        'content': b'test-image-content',
        'filename': 'test.jpg',
        'content_type': 'image/jpeg'
    }

@pytest.fixture
def mock_opencv():
    """Mock OpenCV functions"""
    with patch('cv2.imread') as mock_imread, \
         patch('cv2.resize') as mock_resize, \
         patch('cv2.cvtColor') as mock_cvtcolor:
        
        mock_imread.return_value = Mock()
        mock_resize.return_value = Mock()
        mock_cvtcolor.return_value = Mock()
        
        yield {
            'imread': mock_imread,
            'resize': mock_resize,
            'cvtcolor': mock_cvtcolor
        }

@pytest.fixture
def mock_pillow():
    """Mock Pillow functions"""
    with patch('PIL.Image.open') as mock_open, \
         patch('PIL.Image.fromarray') as mock_fromarray:
        
        mock_image = Mock()
        mock_open.return_value = mock_image
        mock_fromarray.return_value = mock_image
        
        yield {
            'open': mock_open,
            'fromarray': mock_fromarray,
            'image': mock_image
        } 