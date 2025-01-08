# AttendanceAI - Face Recognition Attendance System

A modern web-based attendance management system using facial recognition technology. Built with Flask, AWS Rekognition, and Firebase.

## Features

- 🎯 Face Recognition-based Attendance
- 👥 Student & Teacher Management
- 📊 Real-time Attendance Dashboard
- 📅 Attendance History & Reports
- 📱 Responsive Design
- 🔒 Role-based Access Control

## Tech Stack

- **Backend**: Python Flask
- **Database**: Firebase Firestore
- **Face Recognition**: AWS Rekognition
- **Frontend**: HTML, JavaScript, TailwindCSS, DaisyUI
- **Authentication**: Firebase Auth

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

2. Create and activate virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up Firebase:
   - Create a new Firebase project
   - Enable Authentication and Firestore
   - Download service account key and save as `firebase_credentials.json`

5. Set up AWS:
   - Create an AWS account
   - Set up IAM user with Rekognition access
   - Configure AWS credentials

## Running the Application

1. Start the Flask server:
   ```bash
   flask run
   ```

2. Access the application at `http://localhost:5000`

## Project Structure

```
attendance-keeper/
├── app/
│   ├── routes/
│   │   ├── admin.py      # Admin routes
│   │   ├── auth.py       # Authentication routes
│   │   ├── main.py       # Main routes
│   │   └── recognition.py # Face recognition routes
│   ├── templates/
│   │   ├── admin/        # Admin templates
│   │   ├── auth/         # Auth templates
│   │   └── dashboard.html # Main dashboard
│   ├── static/
│   │   ├── css/          # Stylesheets
│   │   └── js/           # JavaScript files
│   └── __init__.py       # App initialization
├── requirements.txt
└── README.md
```

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `GET /auth/logout` - User logout

### Face Recognition
- `POST /recognition/register` - Register a new face
- `POST /recognize` - Recognize faces in image

### Student Management
- `GET /api/students` - Get all students
- `GET /api/students/template` - Download student template
- `POST /api/students/upload` - Upload student data

### Attendance
- `GET /api/attendance` - Get attendance records
- `GET /api/attendance/download` - Download attendance report

## User Roles

1. **Admin**
   - Manage students and teachers
   - View all attendance records
   - Generate reports
   - Register faces

2. **Teacher**
   - Take attendance using face recognition
   - View class attendance
   - Register student faces
   - Download reports

3. **Student**
   - View personal attendance
   - Check attendance history

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

