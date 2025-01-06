"""Tests for database service functionality"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.services.db_service import DatabaseService

def test_init(app, mock_db):
    """Test DatabaseService initialization"""
    service = DatabaseService()
    assert service.db is not None
    assert service.logger is not None

def test_create_user(app, mock_db, test_user):
    """Test user creation"""
    service = DatabaseService()
    
    # Mock document reference
    doc_ref = mock_db.collection().document()
    doc_ref.get.return_value = Mock(exists=False)
    doc_ref.set.return_value = None
    
    result = service.create_user(
        username=test_user['username'],
        password=test_user['password_hash'],
        role=test_user['role'],
        email=test_user['email']
    )
    
    assert isinstance(result, str)
    doc_ref.set.assert_called_once()

def test_get_user(app, mock_db, test_user):
    """Test user retrieval"""
    service = DatabaseService()
    
    # Mock document snapshot
    doc_snapshot = Mock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = test_user
    doc_snapshot.id = test_user['id']
    
    mock_db.collection().document().get.return_value = doc_snapshot
    
    result = service.get_user(test_user['id'])
    
    assert result is not None
    assert result['username'] == test_user['username']
    assert result['role'] == test_user['role']

def test_get_user_by_username(app, mock_db, test_user):
    """Test user retrieval by username"""
    service = DatabaseService()
    
    # Mock query snapshot
    query_snapshot = Mock()
    doc_snapshot = Mock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = test_user
    doc_snapshot.id = test_user['id']
    query_snapshot.empty = False
    query_snapshot.docs = [doc_snapshot]
    
    mock_db.collection().where().get.return_value = query_snapshot
    
    result = service.get_user_by_username(test_user['username'])
    
    assert result is not None
    assert result['username'] == test_user['username']
    assert result['role'] == test_user['role']

def test_create_subject(app, mock_db, test_subject):
    """Test subject creation"""
    service = DatabaseService()
    
    # Mock document reference
    doc_ref = mock_db.collection().document()
    doc_ref.get.return_value = Mock(exists=False)
    doc_ref.set.return_value = None
    
    result = service.create_subject(
        name=test_subject['name'],
        code=test_subject['code'],
        teacher_id=test_subject['teacher_id'],
        schedule=test_subject['schedule']
    )
    
    assert isinstance(result, str)
    doc_ref.set.assert_called_once()

def test_get_subjects(app, mock_db, test_subject):
    """Test subject retrieval"""
    service = DatabaseService()
    
    # Mock query snapshot
    query_snapshot = Mock()
    doc_snapshot = Mock()
    doc_snapshot.exists = True
    doc_snapshot.to_dict.return_value = test_subject
    doc_snapshot.id = test_subject['id']
    query_snapshot.empty = False
    query_snapshot.docs = [doc_snapshot]
    
    mock_db.collection().get.return_value = query_snapshot
    
    result = service.get_subjects()
    
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]['name'] == test_subject['name']
    assert result[0]['code'] == test_subject['code']

def test_log_attendance(app, mock_db, test_attendance):
    """Test attendance logging"""
    service = DatabaseService()
    
    # Mock document reference
    doc_ref = mock_db.collection().document()
    doc_ref.set.return_value = None
    
    result = service.log_attendance(
        student_id=test_attendance[0]['student_id'],
        subject_id=test_attendance[0]['subject_id'],
        status=test_attendance[0]['status'],
        confidence=test_attendance[0]['confidence']
    )
    
    assert isinstance(result, str)
    doc_ref.set.assert_called_once()

def test_get_attendance(app, mock_db, test_attendance):
    """Test attendance retrieval"""
    service = DatabaseService()
    
    # Mock query snapshot
    query_snapshot = Mock()
    doc_snapshots = []
    for record in test_attendance:
        doc_snapshot = Mock()
        doc_snapshot.exists = True
        doc_snapshot.to_dict.return_value = record
        doc_snapshot.id = record['id']
        doc_snapshots.append(doc_snapshot)
    
    query_snapshot.empty = False
    query_snapshot.docs = doc_snapshots
    
    mock_db.collection().get.return_value = query_snapshot
    
    result = service.get_attendance()
    
    assert isinstance(result, list)
    assert len(result) == len(test_attendance)
    assert result[0]['student_id'] == test_attendance[0]['student_id']
    assert result[0]['status'] == test_attendance[0]['status']

def test_update_attendance(app, mock_db, test_attendance):
    """Test attendance update"""
    service = DatabaseService()
    
    # Mock document reference
    doc_ref = mock_db.collection().document()
    doc_ref.get.return_value = Mock(exists=True)
    doc_ref.update.return_value = None
    
    result = service.update_attendance(
        test_attendance[0]['id'],
        {'status': 'excused'}
    )
    
    assert result is True
    doc_ref.update.assert_called_once()

def test_delete_attendance(app, mock_db, test_attendance):
    """Test attendance deletion"""
    service = DatabaseService()
    
    # Mock document reference
    doc_ref = mock_db.collection().document()
    doc_ref.get.return_value = Mock(exists=True)
    doc_ref.delete.return_value = None
    
    result = service.delete_attendance(test_attendance[0]['id'])
    
    assert result is True
    doc_ref.delete.assert_called_once()

def test_get_attendance_stats(app, mock_db, test_attendance):
    """Test attendance statistics calculation"""
    service = DatabaseService()
    
    # Mock query snapshots
    query_snapshot = Mock()
    doc_snapshots = []
    for record in test_attendance:
        doc_snapshot = Mock()
        doc_snapshot.exists = True
        doc_snapshot.to_dict.return_value = record
        doc_snapshot.id = record['id']
        doc_snapshots.append(doc_snapshot)
    
    query_snapshot.empty = False
    query_snapshot.docs = doc_snapshots
    
    mock_db.collection().get.return_value = query_snapshot
    
    result = service.get_attendance_stats(test_attendance[0]['student_id'])
    
    assert isinstance(result, dict)
    assert 'total_classes' in result
    assert 'present_count' in result
    assert 'absent_count' in result
    assert 'attendance_rate' in result

def test_error_handling(app, mock_db):
    """Test error handling in database service"""
    service = DatabaseService()
    
    # Mock database errors
    mock_db.collection().document().get.side_effect = Exception("Database Error")
    mock_db.collection().document().set.side_effect = Exception("Database Error")
    
    # Test user creation error
    result = service.create_user("test", "pass", "student", "test@test.com")
    assert result is None
    
    # Test user retrieval error
    result = service.get_user("test-id")
    assert result is None
    
    # Test subject creation error
    result = service.create_subject("Test", "TST101", "teacher-id", {})
    assert result is None
    
    # Test attendance logging error
    result = service.log_attendance("student-id", "subject-id", "present", 99.9)
    assert result is None

def test_batch_operations(app, mock_db, test_attendance):
    """Test batch operations"""
    service = DatabaseService()
    
    # Mock batch operations
    batch = Mock()
    mock_db.batch.return_value = batch
    
    # Test batch attendance logging
    attendance_records = [
        {
            'student_id': record['student_id'],
            'subject_id': record['subject_id'],
            'status': record['status'],
            'confidence': record['confidence']
        }
        for record in test_attendance
    ]
    
    result = service.log_attendance_batch(attendance_records)
    
    assert result is True
    assert batch.commit.called

def test_query_filters(app, mock_db, test_attendance):
    """Test query filters"""
    service = DatabaseService()
    
    # Mock query snapshots
    query_snapshot = Mock()
    doc_snapshots = []
    for record in test_attendance:
        doc_snapshot = Mock()
        doc_snapshot.exists = True
        doc_snapshot.to_dict.return_value = record
        doc_snapshot.id = record['id']
        doc_snapshots.append(doc_snapshot)
    
    query_snapshot.empty = False
    query_snapshot.docs = doc_snapshots
    
    mock_db.collection().where().where().get.return_value = query_snapshot
    
    # Test filtered attendance retrieval
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()
    
    result = service.get_attendance(
        student_id=test_attendance[0]['student_id'],
        subject_id=test_attendance[0]['subject_id'],
        start_date=start_date,
        end_date=end_date
    )
    
    assert isinstance(result, list)
    assert len(result) > 0 