# AttendanceAI - Face Recognition Attendance System

A modern, AI-powered attendance management system built with Flask, AWS Rekognition, and Firebase. The system uses facial recognition to automate attendance tracking for educational institutions.

## Features

- **Face Recognition Attendance**
  - Real-time face detection and recognition
  - Support for group photos
  - Progress tracking during recognition
  - High accuracy with AWS Rekognition

- **User Management**
  - Multi-role system (Admin, Teacher, Student)
  - Secure authentication
  - Profile management
  - Bulk user import via Excel

- **Attendance Management**
  - Real-time attendance tracking
  - Historical attendance records
  - Attendance reports and analytics
  - Export functionality
  - Subject-wise attendance

- **Dashboard**
  - Real-time statistics
  - Attendance trends visualization
  - Recent activity feed
  - Role-based views

## Tech Stack

- **Backend**: Python Flask
- **Database**: Firebase Firestore
- **Face Recognition**: AWS Rekognition
- **Frontend**: 
  - HTML/Jinja2 Templates
  - TailwindCSS
  - DaisyUI Components
  - Chart.js for visualizations
  - Remix Icons

## Prerequisites

- Python 3.11+
- AWS Account with Rekognition access
- Firebase Project
- Node.js and npm (for TailwindCSS)

## Environment Variables

Create a `.env` file with the following:

```env
FLASK_APP=app
FLASK_ENV=development
SECRET_KEY=your-secret-key

# AWS Credentials
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=your-aws-region

# Firebase
FIREBASE_CREDENTIALS=path-to-firebase-credentials.json
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/attendance-keeper.git
   cd attendance-keeper
   ```

2. Create and activate virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install frontend dependencies:
   ```bash
   npm install
   ```

5. Build CSS:
   ```bash
   npm run build-css
   ```

6. Initialize the database:
   ```bash
   flask init-db
   ```

## Running the Application

1. Start the Flask development server:
   ```bash
   flask run
   ```

2. Access the application at `http://localhost:5000`

## Project Structure

```
attendance-keeper/
├── app/
│   ├── static/          # Static files (CSS, JS)
│   ├── templates/       # Jinja2 templates
│   ├── routes/          # Route handlers
│   ├── services/        # Business logic
│   └── utils/           # Utility functions
├── instance/           # Instance-specific files
├── tests/             # Test suite
├── .env               # Environment variables
├── requirements.txt   # Python dependencies
└── README.md         # This file
```

## API Endpoints

### Authentication
- `POST /login`: User login
- `GET /logout`: User logout

### Dashboard
- `GET /`: Main dashboard
- `GET /dashboard`: Dashboard (alternate route)

### Attendance
- `POST /recognition/register`: Register a new face
- `POST /recognition/recognize`: Recognize faces in image
- `GET /attendance/`: View attendance records
- `GET /attendance/export`: Export attendance data

### Admin Routes
- `GET /admin/students`: Manage students
- `GET /admin/users`: Manage users
- `GET /admin/subjects`: Manage subjects

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- AWS Rekognition for face recognition
- Firebase for database management
- TailwindCSS and DaisyUI for UI components
- Chart.js for data visualization

