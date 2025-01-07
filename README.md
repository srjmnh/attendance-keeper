# AttendanceAI - Facial Recognition Attendance System

A modern attendance management system using facial recognition, built with Flask, Firebase, and AWS Rekognition.

## Features

### Core Functionality
- 🔐 **User Authentication**
  - Role-based access (Admin, Teacher, Student)
  - Secure password management
  - Profile customization

- 👤 **Facial Recognition**
  - Face registration for students
  - Real-time face detection and recognition
  - Multi-face recognition support

- 📊 **Attendance Management**
  - Automated attendance tracking
  - Subject-wise attendance records
  - Excel import/export functionality

- 📚 **Subject Management**
  - Create and manage subjects
  - Assign teachers to subjects
  - Track subject-wise attendance

### Additional Features
- 📧 **Email Notifications**
  - Attendance confirmations
  - Low attendance alerts
  - System notifications

- 💬 **AI Chat Assistant**
  - Powered by Google's Gemini
  - Context-aware responses
  - Usage guidance and support

- 🎨 **Modern UI/UX**
  - Responsive design
  - Tailwind CSS styling
  - Interactive dashboard

## Tech Stack

- **Backend**: Python Flask
- **Database**: Firebase Firestore
- **Authentication**: Firebase Auth
- **Storage**: Firebase Storage
- **Face Recognition**: AWS Rekognition
- **Frontend**: HTML, Tailwind CSS, JavaScript
- **AI Chat**: Google Gemini API

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd attendance-keeper
   ```

2. **Set Up Python Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**
   Create a `.env` file with:
   ```
   FLASK_APP=run.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key
   
   # Firebase
   FIREBASE_ADMIN_CREDENTIALS_BASE64=your-base64-encoded-credentials
   
   # AWS
   AWS_ACCESS_KEY_ID=your-aws-access-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret-key
   AWS_REGION=your-aws-region
   AWS_REKOGNITION_COLLECTION=attendance-faces
   
   # Email
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=true
   MAIL_USERNAME=your-email
   MAIL_PASSWORD=your-app-password
   MAIL_DEFAULT_SENDER=noreply@attendanceai.com
   
   # Gemini
   GEMINI_API_KEY=your-gemini-api-key
   ```

4. **Initialize Firebase**
   - Create a Firebase project
   - Download service account key
   - Base64 encode the key and add to environment variables

5. **Set Up AWS**
   - Create an AWS account
   - Set up IAM user with Rekognition access
   - Add credentials to environment variables

6. **Run the Application**
   ```bash
   flask run
   ```

## Usage

### Admin
- Create and manage users
- Add/remove subjects
- View all attendance records
- Generate reports

### Teacher
- Register student faces
- Take attendance using facial recognition
- Manage subject attendance
- Export attendance reports

### Student
- View personal attendance records
- Receive attendance notifications
- Update profile information

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

