# Facial Recognition Attendance System

A modern, AI-powered attendance management system using facial recognition and intelligent insights.

## Features

### Core Features
- Facial recognition-based attendance using AWS Rekognition
- Real-time attendance tracking and monitoring
- Multi-role support (Admin, Teacher, Student)
- Subject and class management
- Comprehensive attendance reporting

### AI Capabilities
- Smart attendance pattern analysis
- Personalized insights and recommendations
- Schedule optimization suggestions
- Engagement strategy recommendations
- AI-powered chatbot assistance

### Technical Features
- Image enhancement and quality validation
- Real-time face detection and recognition
- Secure user authentication and authorization
- Rate limiting and security measures
- Responsive web interface

## Technology Stack

### Backend
- Python 3.8+
- Flask web framework
- AWS Rekognition for facial recognition
- Firebase Firestore for database
- Google Gemini AI for intelligent features
- OpenCV and Pillow for image processing

### Frontend
- HTML5, CSS3, JavaScript
- Bootstrap 5 for responsive design
- Font Awesome icons
- AJAX for asynchronous updates

### Infrastructure
- Render for deployment
- Redis for caching (optional)
- AWS S3 for image storage
- Firebase Admin SDK

## Project Structure

```
attendance-keeper/
├── app/
│   ├── models/
│   │   ├── user.py
│   │   ├── attendance.py
│   │   └── subject.py
│   ├── services/
│   │   ├── ai_service.py
│   │   ├── face_service.py
│   │   └── db_service.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── attendance.py
│   │   ├── recognition.py
│   │   └── chat.py
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard/
│   │   ├── attendance/
│   │   └── chat/
│   └── static/
│       ├── css/
│       ├── js/
│       └── img/
├── tests/
│   ├── test_ai_service.py
│   ├── test_face_service.py
│   ├── test_db_service.py
│   └── test_api.py
├── requirements.txt
├── render.yaml
└── run.py
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/attendance-keeper.git
cd attendance-keeper
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration values
```

5. Run the application:
```bash
python run.py
```

## Configuration

Required environment variables:
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_REGION`: AWS region (e.g., us-east-1)
- `FIREBASE_ADMIN_CREDENTIALS_BASE64`: Base64-encoded Firebase admin credentials
- `GEMINI_API_KEY`: Google Gemini AI API key
- `SECRET_KEY`: Flask secret key
- `PORT`: Application port (default: 5000)

## API Documentation

### Authentication
- `POST /api/auth/login`: User login
- `POST /api/auth/logout`: User logout
- `POST /api/auth/refresh`: Refresh authentication token

### Face Recognition
- `POST /api/recognition/register`: Register a new face
- `POST /api/recognition/recognize`: Recognize faces in image
- `DELETE /api/recognition/delete`: Delete a registered face

### Attendance
- `GET /api/attendance`: Get attendance records
- `POST /api/attendance`: Log attendance
- `GET /api/attendance/stats`: Get attendance statistics
- `POST /api/attendance/report`: Generate attendance report

### AI Features
- `POST /api/chat/message`: Send message to AI assistant
- `POST /api/attendance/analyze`: Analyze attendance patterns
- `POST /api/schedule/optimize`: Get schedule optimization suggestions

## Testing

Run the test suite:
```bash
pytest
```

Run specific tests:
```bash
pytest tests/test_ai_service.py
pytest tests/test_face_service.py
pytest tests/test_db_service.py
pytest tests/test_api.py
```

## Recent Updates

### Implemented Components
- AI Service with Gemini integration
- Face Recognition Service with AWS Rekognition
- Database Service with Firebase
- Frontend templates (base, dashboard, chat)
- Custom CSS and JavaScript utilities
- Comprehensive test suite

### In Progress
- Additional frontend templates
- API routes implementation
- CI/CD configuration
- Deployment scripts

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

