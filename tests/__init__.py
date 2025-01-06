"""
Tests Package
-----------

This package contains test cases for the application.
The tests are organized by feature and use pytest.

Test Categories:
- Unit Tests: Test individual components
  - test_models.py: Test data models
  - test_services.py: Test service classes
  - test_routes.py: Test API endpoints

- Integration Tests: Test component interactions
  - test_face_recognition.py: Test face recognition flow
  - test_attendance.py: Test attendance flow
  - test_chat.py: Test AI chat flow

- End-to-End Tests: Test complete workflows
  - test_user_workflow.py: Test user management workflow
  - test_attendance_workflow.py: Test attendance workflow
  - test_chat_workflow.py: Test chat workflow

Usage:
    pytest                 # Run all tests
    pytest tests/unit/     # Run unit tests
    pytest -v              # Run tests with verbose output
    pytest -k "face"       # Run tests matching "face"
    pytest --cov=app      # Run tests with coverage
""" 