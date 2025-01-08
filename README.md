# AttendanceAI - Face Recognition Attendance System

A modern web-based attendance management system using facial recognition technology. Built with Flask, AWS Rekognition, and Firebase.

## Features

### Core Features
- 🎯 Face Recognition-based Attendance
  - Real-time face detection and recognition
  - Support for multiple faces in one image
  - Enhanced image processing for better accuracy
  - Confidence score for each recognition

### Attendance Management
- 📊 Comprehensive Attendance Dashboard
  - Real-time attendance tracking
  - Detailed attendance records with timestamps
  - Inline editing of attendance records
  - Bulk attendance updates
  - Export to Excel functionality

### Filtering & Search
- 🔍 Advanced Filtering Options
  - Date range filters (Today, Week, Month, Custom)
  - Subject-wise filtering
  - Status-based filtering (Present/Absent)
  - Search by student name or ID
  - Combined filters support

### User Management
- 👥 Role-based Access Control
  - Admin: Full system access
  - Teacher: Class-specific access
  - Student: Personal attendance view
- 📱 Responsive Design for all devices

## Tech Stack

- **Backend**: Python Flask
- **Database**: Firebase Firestore
- **Face Recognition**: AWS Rekognition
- **Frontend**: 
  - HTML, JavaScript
  - TailwindCSS
  - DaisyUI for components
- **Authentication**: Firebase Auth
- **File Storage**: AWS S3

## File Structure

```
attendance-keeper/
├── app/
│   ├── routes/
│   │   ├── admin.py        # Admin panel routes
│   │   ├── attendance.py   # Attendance management
│   │   ├── auth.py        # Authentication routes
│   │   ├── main.py        # Dashboard routes
│   │   └── recognition.py # Face recognition endpoints
│   ├── services/
│   │   ├── db_service.py      # Database operations
│   │   ├── rekognition_service.py # AWS Rekognition
│   │   └── gemini_service.py  # AI Assistant
│   ├── templates/
│   │   ├── admin/
│   │   │   ├── dashboard.html # Admin dashboard
│   │   │   ├── students.html  # Student management
│   │   │   └── subjects.html  # Subject management
│   │   ├── attendance/
│   │   │   ├── manage.html    # Take attendance
│   │   │   └── view.html      # View/edit attendance
│   │   ├── auth/
│   │   │   ├── login.html     # Login page
│   │   │   └── register.html  # Registration
│   │   ├── base.html          # Base template
│   │   └── dashboard.html     # Main dashboard
│   ├── static/
│   │   ├── css/
│   │   │   └── main.css       # Custom styles
│   │   └── js/
│   │       └── main.js        # Common JavaScript
│   └── __init__.py           # App initialization
├── requirements.txt          # Python dependencies
└── run.py                   # Application entry point
```

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `GET /auth/logout` - User logout

### Face Recognition
- `POST /recognition/register` - Register a new face
- `POST /recognize` - Recognize faces in image

### Attendance Management
- `GET /attendance/view` - View attendance records
- `GET /api/attendance` - Get filtered attendance records
- `POST /api/attendance/update` - Update attendance records
- `DELETE /api/attendance/<id>` - Delete attendance record
- `GET /api/attendance/export` - Export attendance to Excel
- `POST /api/attendance/upload` - Upload attendance from Excel

### Student Management
- `GET /admin/students` - View all students
- `POST /admin/students` - Add new student
- `PUT /admin/students/<id>` - Update student
- `DELETE /admin/students/<id>` - Delete student

## Prerequisites

1. Python 3.8+
2. AWS Account with Rekognition access
3. Firebase Project
4. Node.js and npm (for development)

## Environment Variables

Create a `.env` file in the root directory with:

```env
FLASK_APP=app
FLASK_ENV=development
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=your_aws_region
FIREBASE_CREDENTIALS=path_to_firebase_credentials.json
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/attendance-keeper.git
   cd attendance-keeper
   ```

2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   flask run
   ```

## User Roles

1. **Admin**
   - Manage students and teachers
   - View and edit all attendance records
   - Generate reports
   - Register faces
   - Delete records

2. **Teacher**
   - Take attendance using face recognition
   - View and edit class attendance
   - Register student faces
   - Download reports

3. **Student**
   - View personal attendance
   - Check attendance history
   - Download personal reports

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, email your.email@example.com or open an issue in the repository.

