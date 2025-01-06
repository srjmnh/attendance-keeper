"""Tests for face recognition service functionality"""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from io import BytesIO
from PIL import Image

from app.services.face_service import FaceService

@pytest.fixture
def sample_image_array():
    """Create a sample image array for testing"""
    return np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

@pytest.fixture
def sample_image_bytes(sample_image_array):
    """Create sample image bytes for testing"""
    img = Image.fromarray(sample_image_array)
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    return buffer.getvalue()

def test_init(app, mock_rekognition):
    """Test FaceService initialization"""
    service = FaceService()
    assert service.rekognition is not None
    assert service.collection_id == app.config['AWS_COLLECTION_ID']
    assert service.logger is not None

def test_enhance_image(app, mock_opencv, mock_pillow, sample_image_array):
    """Test image enhancement"""
    service = FaceService()
    
    # Mock OpenCV and Pillow operations
    mock_opencv['imread'].return_value = sample_image_array
    mock_opencv['resize'].return_value = sample_image_array
    mock_opencv['cvtcolor'].return_value = sample_image_array
    mock_pillow['image'].enhance.return_value = mock_pillow['image']
    
    result = service.enhance_image(sample_image_bytes)
    
    assert isinstance(result, bytes)
    assert len(result) > 0

def test_register_face(app, mock_rekognition, sample_image_bytes):
    """Test face registration"""
    service = FaceService()
    
    # Mock AWS Rekognition response
    mock_rekognition.index_faces.return_value = {
        'FaceRecords': [{
            'Face': {
                'FaceId': 'test-face-id',
                'Confidence': 99.9,
                'Quality': {'Brightness': 90.0, 'Sharpness': 95.0}
            }
        }]
    }
    
    result = service.register_face(sample_image_bytes)
    
    assert 'face_id' in result
    assert 'confidence' in result
    assert 'quality' in result
    assert result['face_id'] == 'test-face-id'
    assert result['confidence'] == 99.9

def test_detect_faces(app, mock_rekognition, sample_image_bytes):
    """Test face detection"""
    service = FaceService()
    
    # Mock AWS Rekognition response
    mock_rekognition.detect_faces.return_value = {
        'FaceDetails': [{
            'Confidence': 99.9,
            'BoundingBox': {
                'Width': 0.5,
                'Height': 0.5,
                'Left': 0.25,
                'Top': 0.25
            },
            'Quality': {'Brightness': 90.0, 'Sharpness': 95.0}
        }]
    }
    
    result = service.detect_faces(sample_image_bytes)
    
    assert isinstance(result, list)
    assert len(result) == 1
    assert 'confidence' in result[0]
    assert 'bounding_box' in result[0]
    assert 'quality' in result[0]

def test_search_faces(app, mock_rekognition, sample_image_bytes):
    """Test face searching"""
    service = FaceService()
    
    # Mock AWS Rekognition responses
    mock_rekognition.detect_faces.return_value = {
        'FaceDetails': [{
            'Confidence': 99.9,
            'BoundingBox': {
                'Width': 0.5,
                'Height': 0.5,
                'Left': 0.25,
                'Top': 0.25
            }
        }]
    }
    
    mock_rekognition.search_faces_by_image.return_value = {
        'FaceMatches': [{
            'Face': {
                'FaceId': 'test-face-id',
                'Confidence': 99.9
            },
            'Similarity': 98.5
        }]
    }
    
    result = service.search_faces(sample_image_bytes)
    
    assert isinstance(result, list)
    assert len(result) == 1
    assert 'face_id' in result[0]
    assert 'confidence' in result[0]
    assert 'similarity' in result[0]

def test_delete_face(app, mock_rekognition):
    """Test face deletion"""
    service = FaceService()
    face_id = 'test-face-id'
    
    # Mock AWS Rekognition response
    mock_rekognition.delete_faces.return_value = {
        'DeletedFaces': [face_id]
    }
    
    result = service.delete_face(face_id)
    
    assert result is True
    mock_rekognition.delete_faces.assert_called_once_with(
        CollectionId=service.collection_id,
        FaceIds=[face_id]
    )

def test_validate_face_quality(app, mock_rekognition, sample_image_bytes):
    """Test face quality validation"""
    service = FaceService()
    
    # Mock AWS Rekognition response
    mock_rekognition.detect_faces.return_value = {
        'FaceDetails': [{
            'Confidence': 99.9,
            'Quality': {
                'Brightness': 90.0,
                'Sharpness': 95.0
            },
            'Pose': {
                'Pitch': 0.0,
                'Roll': 0.0,
                'Yaw': 0.0
            }
        }]
    }
    
    result = service._validate_face_quality(sample_image_bytes)
    
    assert result['is_valid'] is True
    assert 'quality_score' in result
    assert 'issues' in result

def test_error_handling(app, mock_rekognition, sample_image_bytes):
    """Test error handling in face service"""
    service = FaceService()
    
    # Test registration error
    mock_rekognition.index_faces.side_effect = Exception("AWS Error")
    result = service.register_face(sample_image_bytes)
    assert 'error' in result
    
    # Test detection error
    mock_rekognition.detect_faces.side_effect = Exception("AWS Error")
    result = service.detect_faces(sample_image_bytes)
    assert isinstance(result, list)
    assert len(result) == 0
    
    # Test search error
    mock_rekognition.search_faces_by_image.side_effect = Exception("AWS Error")
    result = service.search_faces(sample_image_bytes)
    assert isinstance(result, list)
    assert len(result) == 0
    
    # Test deletion error
    mock_rekognition.delete_faces.side_effect = Exception("AWS Error")
    result = service.delete_face("test-face-id")
    assert result is False

def test_image_preprocessing(app, mock_opencv, mock_pillow, sample_image_array):
    """Test image preprocessing"""
    service = FaceService()
    
    # Mock image processing operations
    mock_opencv['imread'].return_value = sample_image_array
    mock_opencv['resize'].return_value = sample_image_array
    mock_opencv['cvtcolor'].return_value = sample_image_array
    mock_pillow['image'].enhance.return_value = mock_pillow['image']
    
    # Test with valid image
    result = service._preprocess_image(sample_image_bytes)
    assert isinstance(result, bytes)
    assert len(result) > 0
    
    # Test with invalid image
    mock_opencv['imread'].return_value = None
    result = service._preprocess_image(b'invalid image data')
    assert result is None

def test_face_quality_thresholds(app, mock_rekognition, sample_image_bytes):
    """Test face quality threshold checks"""
    service = FaceService()
    
    # Test high quality face
    mock_rekognition.detect_faces.return_value = {
        'FaceDetails': [{
            'Confidence': 99.9,
            'Quality': {
                'Brightness': 90.0,
                'Sharpness': 95.0
            },
            'Pose': {
                'Pitch': 0.0,
                'Roll': 0.0,
                'Yaw': 0.0
            }
        }]
    }
    result = service._validate_face_quality(sample_image_bytes)
    assert result['is_valid'] is True
    
    # Test low quality face
    mock_rekognition.detect_faces.return_value = {
        'FaceDetails': [{
            'Confidence': 60.0,
            'Quality': {
                'Brightness': 40.0,
                'Sharpness': 45.0
            },
            'Pose': {
                'Pitch': 45.0,
                'Roll': 45.0,
                'Yaw': 45.0
            }
        }]
    }
    result = service._validate_face_quality(sample_image_bytes)
    assert result['is_valid'] is False
    assert len(result['issues']) > 0

def test_multiple_faces(app, mock_rekognition, sample_image_bytes):
    """Test handling of multiple faces in image"""
    service = FaceService()
    
    # Mock multiple faces detection
    mock_rekognition.detect_faces.return_value = {
        'FaceDetails': [
            {
                'Confidence': 99.9,
                'BoundingBox': {'Width': 0.3, 'Height': 0.3, 'Left': 0.1, 'Top': 0.1}
            },
            {
                'Confidence': 98.5,
                'BoundingBox': {'Width': 0.3, 'Height': 0.3, 'Left': 0.6, 'Top': 0.1}
            }
        ]
    }
    
    result = service.detect_faces(sample_image_bytes)
    
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]['confidence'] > result[1]['confidence'] 