"""Tests for API endpoints"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch

def test_login(client):
    """Test login endpoint"""
    response = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'token' in data
    assert 'user' in data

def test_login_invalid_credentials(client):
    """Test login with invalid credentials"""
    response = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'wrongpass'
    })
    
    assert response.status_code == 401
    data = json.loads(response.data)
    assert 'error' in data

def test_register_face(client, auth_headers, sample_image, mock_services):
    """Test face registration endpoint"""
    response = client.post('/api/recognition/register', data={
        'image': (sample_image['content'], sample_image['filename']),
        'student_id': 'test-student-id'
    }, headers=auth_headers)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'face_id' in data
    assert 'confidence' in data

def test_recognize_faces(client, auth_headers, sample_image, mock_services):
    """Test face recognition endpoint"""
    response = client.post('/api/recognition/recognize', data={
        'image': (sample_image['content'], sample_image['filename']),
        'subject_id': 'test-subject-id'
    }, headers=auth_headers)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'matches' in data
    assert isinstance(data['matches'], list)

def test_get_attendance(client, auth_headers, test_attendance, mock_services):
    """Test attendance retrieval endpoint"""
    response = client.get('/api/attendance', headers=auth_headers)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) > 0

def test_get_attendance_filtered(client, auth_headers, test_attendance, mock_services):
    """Test filtered attendance retrieval"""
    response = client.get('/api/attendance', query_string={
        'student_id': test_attendance[0]['student_id'],
        'subject_id': test_attendance[0]['subject_id'],
        'start_date': datetime.now().isoformat(),
        'end_date': datetime.now().isoformat()
    }, headers=auth_headers)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)

def test_get_attendance_stats(client, auth_headers, test_attendance, mock_services):
    """Test attendance statistics endpoint"""
    response = client.get(f'/api/attendance/stats/{test_attendance[0]["student_id"]}',
                         headers=auth_headers)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'attendance_rate' in data
    assert 'total_classes' in data

def test_generate_report(client, auth_headers, test_attendance, mock_services):
    """Test report generation endpoint"""
    response = client.post('/api/attendance/report', json={
        'student_id': test_attendance[0]['student_id'],
        'start_date': datetime.now().isoformat(),
        'end_date': datetime.now().isoformat()
    }, headers=auth_headers)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'report' in data
    assert 'insights' in data

def test_chat_message(client, auth_headers, mock_services):
    """Test AI chat endpoint"""
    response = client.post('/api/chat/message', json={
        'message': 'Test message',
        'context': {'user_role': 'student'}
    }, headers=auth_headers)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'message' in data
    assert 'suggestions' in data

def test_analyze_patterns(client, auth_headers, test_attendance, mock_services):
    """Test attendance pattern analysis endpoint"""
    response = client.post('/api/attendance/analyze', json={
        'student_id': test_attendance[0]['student_id'],
        'subject_id': test_attendance[0]['subject_id']
    }, headers=auth_headers)
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'analysis' in data
    assert 'recommendations' in data

def test_unauthorized_access(client):
    """Test unauthorized access to protected endpoints"""
    endpoints = [
        '/api/attendance',
        '/api/recognition/register',
        '/api/recognition/recognize',
        '/api/chat/message'
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 401

def test_invalid_image(client, auth_headers):
    """Test invalid image upload"""
    response = client.post('/api/recognition/register', data={
        'image': (b'invalid image data', 'test.jpg'),
        'student_id': 'test-student-id'
    }, headers=auth_headers)
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data

def test_missing_parameters(client, auth_headers):
    """Test missing required parameters"""
    endpoints = {
        '/api/recognition/register': {'method': 'post', 'data': {}},
        '/api/recognition/recognize': {'method': 'post', 'data': {}},
        '/api/attendance/report': {'method': 'post', 'json': {}}
    }
    
    for endpoint, config in endpoints.items():
        if config['method'] == 'post':
            if 'data' in config:
                response = client.post(endpoint, data=config['data'],
                                    headers=auth_headers)
            else:
                response = client.post(endpoint, json=config['json'],
                                    headers=auth_headers)
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

def test_error_handling(client, auth_headers, mock_services):
    """Test API error handling"""
    # Mock service errors
    mock_services['face_service'].register_face.side_effect = Exception("Service Error")
    mock_services['ai_service'].process_chat.side_effect = Exception("Service Error")
    
    # Test face registration error
    response = client.post('/api/recognition/register', data={
        'image': (b'test image data', 'test.jpg'),
        'student_id': 'test-student-id'
    }, headers=auth_headers)
    
    assert response.status_code == 500
    data = json.loads(response.data)
    assert 'error' in data
    
    # Test chat error
    response = client.post('/api/chat/message', json={
        'message': 'Test message'
    }, headers=auth_headers)
    
    assert response.status_code == 500
    data = json.loads(response.data)
    assert 'error' in data

def test_rate_limiting(client):
    """Test API rate limiting"""
    # Make multiple rapid requests
    for _ in range(10):
        response = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'testpass'
        })
    
    assert response.status_code == 429
    data = json.loads(response.data)
    assert 'error' in data

def test_cors_headers(client):
    """Test CORS headers"""
    response = client.options('/api/auth/login')
    
    assert response.status_code == 200
    assert 'Access-Control-Allow-Origin' in response.headers
    assert 'Access-Control-Allow-Methods' in response.headers
    assert 'Access-Control-Allow-Headers' in response.headers 