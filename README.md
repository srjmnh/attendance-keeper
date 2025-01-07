# AI-Powered Student Attendance System

A modern attendance management system that uses facial recognition and AI to automate student attendance tracking in educational institutions.

## Features

### Core Features
- **Facial Recognition Attendance**
  - Register student faces
  - Mark attendance using face detection
  - Support for multiple faces in one frame
  - Real-time face verification

### User Management
- **Role-based Access Control**
  - Admin: Full system access
  - Teachers: Manage classes and attendance
  - Students: View attendance and register face

### Attendance Management
- **Smart Attendance Tracking**
  - Automated attendance marking using facial recognition
  - Manual attendance management
  - Attendance reports and analytics
  - Class-wise and subject-wise tracking

### AI Integration
- **AWS Rekognition**
  - Face detection and analysis
  - Face comparison and matching
  - Face collection management

- **Google Gemini AI**
  - AI-powered chatbot for queries
  - Natural language processing
  - Context-aware responses

## Technical Stack

### Backend
- **Framework**: Flask (Python)
- **Database**: Firebase Firestore
- **Authentication**: Flask-Login
- **File Storage**: Local storage with AWS S3 support

### AI Services
- AWS Rekognition for facial recognition
- Google Gemini AI for chatbot
- OpenCV for image processing

### Security
- JWT-based authentication
- Password hashing
- Role-based access control
- Secure file uploads

## Environment Variables

```env
# AWS Configuration
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=your_aws_region

# Firebase Configuration
FIREBASE_ADMIN_CREDENTIALS_BASE64=your_base64_encoded_credentials

# API Keys
GEMINI_API_KEY=your_gemini_api_key

# Flask Configuration
SECRET_KEY=your_secret_key
DEBUG=False
```

## Project Structure

```
attendance-keeper/
├── app/
│   ├── models/
│   │   ├── user.py
│   │   ├── subject.py
│   │   └── attendance.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── attendance.py
│   │   ├── recognition.py
│   │   └── ...
│   ├── services/
│   │   ├── db_service.py
│   │   ├── face_service.py
│   │   ├── ai_service.py
│   │   └── image_service.py
│   ├── templates/
│   └── static/
├── scripts/
├── tests/
└── requirements.txt
```

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/attendance-keeper.git
   cd attendance-keeper
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**
   - Create a `.env` file in the root directory
   - Add all required environment variables

5. **Initialize Firebase**
   - Create a Firebase project
   - Enable Firestore
   - Download service account credentials
   - Convert to base64 and add to environment variables

6. **Set Up AWS Services**
   - Create an AWS account
   - Set up IAM user with Rekognition access
   - Add AWS credentials to environment variables

7. **Run the Application**
   ```bash
   python run.py
   ```

## API Documentation

### Authentication Endpoints
- `POST /auth/register`: Register new user
- `POST /auth/login`: User login
- `GET /auth/logout`: User logout

### Attendance Endpoints
- `POST /attendance/mark`: Mark attendance
- `GET /attendance/view`: View attendance records
- `GET /attendance/reports`: Generate reports

### Face Recognition Endpoints
- `POST /recognition/register`: Register face
- `POST /recognition/verify`: Verify face
- `POST /recognition/recognize`: Recognize faces in image

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

