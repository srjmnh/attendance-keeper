# AI-Powered Student Attendance System

A modern attendance management system that uses facial recognition and AI to automate student attendance tracking in educational institutions.

## Default Admin Credentials
- Email: admin@attendance.com
- Password: Admin@123

To create the admin account, visit: `https://your-app-url/auth/create-admin`

## Changelog

### UI Modernization & Admin Fix (2024-02-14)
- Complete UI overhaul:
  - Switched from Font Awesome to Material Icons
  - Added modern gradients and animations
  - Improved form styling with floating labels
  - Enhanced button and input interactions
  - Added smooth transitions and hover effects
  - Implemented responsive design improvements
  - Added better form validation feedback
  - Enhanced alert messages with icons
  - Updated color scheme with CSS variables
  - Added Inter font for better typography
  - Improved chat widget UI/UX

- Fixed admin user creation:
  - Corrected password hashing in admin creation script
  - Fixed user dictionary conversion before database save
  - Added proper error handling and logging

### Blueprint Fixes (2024-02-14)
- Fixed blueprint naming conflicts in route files:
  - Renamed `bp` to `chat` in `app/routes/chat.py` to match import
  - Renamed `bp` to `admin` in `app/routes/admin.py` to match import
  - Renamed `bp` to `main` in `app/routes/main.py` to match import
  - Fixed route function naming conflict in `chat.py` (renamed `chat()` to `handle_chat()`)
  - Updated blueprint imports in `app/__init__.py` to match new names

These changes resolved the following issues:
1. Blueprint registration errors in `app/__init__.py`
2. Function/blueprint naming conflicts causing `AttributeError: 'function' object has no attribute 'route'`
3. Import errors with blueprint names not matching their registration

### Known Issues
- None currently reported

### Development Guidelines
- Use consistent naming for blueprints (match the route file name)
- Avoid naming conflicts between blueprints and route functions
- Follow Flask's blueprint naming conventions
- Follow Material Design principles for UI components
- Use CSS variables for consistent theming
- Implement proper form validation
- Always hash passwords before database storage

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

