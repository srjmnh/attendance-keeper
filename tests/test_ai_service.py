"""Tests for AI service functionality"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.services.ai_service import AIService

def test_init(app, mock_gemini):
    """Test AIService initialization"""
    service = AIService()
    assert service.model is not None
    assert service.db is not None
    assert service.logger is not None

def test_process_chat_without_history(app, mock_gemini, mock_db):
    """Test chat processing without conversation history"""
    service = AIService()
    mock_response = Mock()
    mock_response.text = "Test response with some suggestions and insights."
    service.model.start_chat().send_message.return_value = mock_response

    context = {'user_role': 'student'}
    result = service.process_chat("Test message", context)

    assert 'message' in result
    assert 'suggestions' in result
    assert 'insights' in result
    assert result['message'] == mock_response.text

def test_process_chat_with_history(app, mock_gemini, mock_db):
    """Test chat processing with conversation history"""
    service = AIService()
    mock_response = Mock()
    mock_response.text = "Test response with context."
    service.model.start_chat().send_message.return_value = mock_response

    context = {'user_role': 'teacher'}
    result = service.process_chat("Test message", context, "test-conversation-id")

    assert 'message' in result
    assert 'conversation_id' in result
    assert result['conversation_id'] == "test-conversation-id"

def test_analyze_attendance_patterns(app, mock_gemini):
    """Test attendance pattern analysis"""
    service = AIService()
    mock_response = Mock()
    mock_response.text = """
    Analysis of attendance patterns.
    
    Recommendations for improvement.
    """
    service.model.generate_content.return_value = mock_response

    records = [
        {
            'student_id': 'test-student',
            'subject_id': 'test-subject',
            'timestamp': datetime.now(),
            'status': 'present'
        }
    ]

    result = service.analyze_attendance_patterns(records)

    assert 'analysis' in result
    assert 'recommendations' in result
    assert result['analysis'].strip() == "Analysis of attendance patterns."

def test_analyze_student_patterns(app, mock_gemini):
    """Test student pattern analysis"""
    service = AIService()
    mock_response = Mock()
    mock_response.text = """
    Student attendance analysis.
    
    Areas for improvement.
    """
    service.model.generate_content.return_value = mock_response

    student_data = {
        'id': 'test-student',
        'name': 'Test Student',
        'attendance_rate': 85.5
    }

    result = service.analyze_student_patterns(student_data)

    assert 'analysis' in result
    assert 'recommendations' in result
    assert result['analysis'].strip() == "Student attendance analysis."

def test_suggest_schedule_optimization(app, mock_gemini):
    """Test schedule optimization suggestions"""
    service = AIService()
    mock_response = Mock()
    mock_response.text = """
    Schedule optimization suggestions.
    
    Implementation rationale.
    
    Steps to implement.
    """
    service.model.generate_content.return_value = mock_response

    subject_data = {
        'id': 'test-subject',
        'name': 'Test Subject',
        'current_schedule': 'Monday 9:00'
    }
    context = {'semester': 'Fall 2024'}

    result = service.suggest_schedule_optimization(subject_data, context)

    assert 'suggestions' in result
    assert 'rationale' in result
    assert 'implementation_steps' in result
    assert result['suggestions'].strip() == "Schedule optimization suggestions."

def test_predict_attendance_risk(app, mock_gemini):
    """Test attendance risk prediction"""
    service = AIService()
    mock_response = Mock()
    mock_response.text = """
    Risk analysis results.
    
    Intervention recommendations.
    """
    service.model.generate_content.return_value = mock_response

    student_data = {
        'id': 'test-student',
        'attendance_rate': 65.0,
        'recent_absences': 3
    }

    result = service.predict_attendance_risk(student_data)

    assert 'risk_analysis' in result
    assert 'risk_level' in result
    assert result['risk_level'] == 'high'

def test_generate_personalized_report(app, mock_gemini):
    """Test personalized report generation"""
    service = AIService()
    mock_response = Mock()
    mock_response.text = """
    Attendance Report
    
    1. Overall Summary
    2. Subject Analysis
    3. Recommendations
    """
    service.model.generate_content.return_value = mock_response

    student_data = {'id': 'test-student', 'name': 'Test Student'}
    attendance_data = [
        {'date': '2024-01-01', 'status': 'present'},
        {'date': '2024-01-02', 'status': 'absent'}
    ]

    result = service.generate_personalized_report(student_data, attendance_data)

    assert 'report' in result
    assert 'insights' in result
    assert 'recommendations' in result
    assert "Attendance Report" in result['report']

def test_suggest_engagement_strategies(app, mock_gemini):
    """Test engagement strategy suggestions"""
    service = AIService()
    mock_response = Mock()
    mock_response.text = """
    Engagement strategies.
    
    Implementation details.
    
    Expected outcomes.
    """
    service.model.generate_content.return_value = mock_response

    context = {
        'class_size': 30,
        'subject_type': 'practical',
        'current_engagement': 75.0
    }

    result = service.suggest_engagement_strategies(context)

    assert 'suggestions' in result
    assert 'rationale' in result
    assert 'implementation_steps' in result
    assert result['suggestions'].strip() == "Engagement strategies."

def test_conversation_history_management(app, mock_db):
    """Test conversation history management"""
    service = AIService()
    conversation_id = "test-conversation"
    message = "Test message"
    response = "Test response"

    # Test saving conversation
    service._save_conversation(conversation_id, message, response)
    
    # Verify database calls
    conversation_ref = service.db.collection('conversations').document(conversation_id)
    assert conversation_ref.set.called
    assert conversation_ref.collection('messages').add.call_count == 2

    # Test retrieving conversation
    history = service._get_conversation_history(conversation_id)
    assert isinstance(history, list)

def test_error_handling(app, mock_gemini):
    """Test error handling in AI service"""
    service = AIService()
    service.model.generate_content.side_effect = Exception("API Error")

    # Test error handling in various methods
    result = service.analyze_attendance_patterns([])
    assert 'error' in result

    result = service.analyze_student_patterns({})
    assert 'error' in result

    result = service.suggest_schedule_optimization({}, {})
    assert 'error' in result

    result = service.predict_attendance_risk({})
    assert 'error' in result

def test_response_parsing(app):
    """Test response parsing methods"""
    service = AIService()

    # Test analysis response parsing
    analysis_text = "Analysis\n\nRecommendations"
    result = service._parse_analysis_response(analysis_text)
    assert 'analysis' in result
    assert 'recommendations' in result

    # Test suggestions response parsing
    suggestions_text = "Suggestions\n\nRationale\n\nSteps"
    result = service._parse_suggestions_response(suggestions_text)
    assert 'suggestions' in result
    assert 'rationale' in result
    assert 'implementation_steps' in result

    # Test extracting suggestions
    text = "I suggest doing X. Consider Y. Try Z."
    suggestions = service._extract_suggestions(text)
    assert len(suggestions) == 3

    # Test extracting insights
    text = "We notice A. We observe B. We find C."
    insights = service._extract_insights(text)
    assert len(insights) == 3

def test_risk_level_calculation(app):
    """Test attendance risk level calculation"""
    service = AIService()

    # Test different attendance rates
    assert service._calculate_risk_level({'attendance_rate': 95}) == 'low'
    assert service._calculate_risk_level({'attendance_rate': 80}) == 'medium'
    assert service._calculate_risk_level({'attendance_rate': 70}) == 'high'
    assert service._calculate_risk_level({}) == 'unknown' 