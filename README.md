# Facial Recognition Attendance System

A modern attendance management system using facial recognition, powered by AWS Rekognition, Firebase, and Gemini AI.

## Overview

This system provides an automated way to track attendance using facial recognition technology. It combines the power of AWS Rekognition for facial detection and matching, Firebase for data storage, and Gemini AI for advanced analytics and insights.

## Features

- **Facial Recognition Attendance**
  - Real-time face detection and matching
  - Support for multiple faces in a single image
  - Quality checks and enhancement of uploaded images
  - Configurable matching thresholds

- **User Management**
  - Role-based access control (Admin, User)
  - Secure authentication and authorization
  - User profile management
  - Email verification

- **Course/Subject Management**
  - Create and manage subjects
  - Assign teachers to subjects
  - Track attendance by subject
  - Generate subject-wise reports

- **Attendance Management**
  - Real-time attendance tracking
  - Late attendance marking
  - Attendance reports and analytics
  - Export functionality (PDF, Excel, CSV)

- **AI-Powered Features**
  - Attendance pattern analysis
  - Student engagement insights
  - Personalized recommendations
  - Predictive analytics

## Technology Stack

- **Backend Framework**: Flask 3.0.2
- **Face Recognition**: AWS Rekognition
- **Database**: Firebase Firestore
- **AI/ML**: Google Gemini AI
- **Caching**: Redis
- **Task Queue**: Celery
- **Image Processing**: OpenCV, Pillow
- **Authentication**: JWT, Flask-Login
- **API Documentation**: Swagger/OpenAPI

## Prerequisites

- Python 3.8+
- AWS Account with Rekognition access
- Firebase Project
- Redis Server (for production)
- Google Cloud Project (for Gemini AI)

## Environment Variables

The following environment variables need to be set:

```env
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key
DEBUG=false

# AWS Configuration
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1

# Firebase Configuration
FIREBASE_ADMIN_CREDENTIALS_BASE64=your-base64-encoded-credentials

# Gemini AI Configuration
GEMINI_API_KEY=your-gemini-api-key

# Redis Configuration (Production)
REDIS_URL=your-redis-url

# Optional Configurations
LOG_LEVEL=INFO
CORS_ORIGINS=*
RATELIMIT_DEFAULT=100 per minute
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/attendance-system.git
   cd attendance-system
   ```

2. Create and activate virtual environment:
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
   # Edit .env with your configuration
   ```

5. Initialize Firebase credentials:
   ```bash
   python encode_firebase.py
   # Copy the output to FIREBASE_ADMIN_CREDENTIALS_BASE64 in your environment
   ```

## Running the Application

### Development
```bash
python run.py
```

### Production (with Gunicorn)
```bash
gunicorn run:app
```

## Deployment on Render

1. Connect your GitHub repository to Render
2. Configure environment variables in Render dashboard
3. Set up Redis service (if needed)
4. Deploy the application

## Project Structure

```
attendance-system/
├── app/
│   ├── __init__.py          # Application factory
│   ├── config.py            # Configuration classes
│   ├── models/              # Database models
│   ├── routes/              # Route blueprints
│   └── services/            # Business logic services
├── static/                  # Static files
├── templates/               # HTML templates
├── tests/                   # Test suite
├── uploads/                 # File uploads
├── logs/                    # Application logs
├── requirements.txt         # Dependencies
├── run.py                   # Application entry point
└── README.md               # This file
```

## Services

### Face Service (`app/services/face_service.py`)
- Handles facial recognition operations
- Integrates with AWS Rekognition
- Manages face collection and matching
- Implements image enhancement

### Database Service (`app/services/db_service.py`)
- Manages Firebase Firestore operations
- Handles CRUD operations for users and attendance
- Implements data validation and security

### AI Service (`app/services/ai_service.py`)
- Integrates with Gemini AI
- Provides attendance analytics
- Generates insights and recommendations
- Handles natural language processing

## Security Features

- JWT-based authentication
- Rate limiting
- CORS protection
- Session management
- CSRF protection
- Secure cookie configuration
- Input validation
- Error handling

## Development Tools

- **Code Formatting**: Black
- **Linting**: Flake8
- **Type Checking**: MyPy
- **Testing**: Pytest

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.

## Acknowledgments

- AWS Rekognition for facial recognition capabilities
- Firebase for reliable data storage
- Google for Gemini AI technology
- The Flask community for the excellent web framework

