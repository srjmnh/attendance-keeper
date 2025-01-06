# Student Attendance System

A modern attendance management system using face recognition and AI assistance.

## Features

- Face recognition-based attendance using AWS Rekognition
- Role-based access control (Admin, Teacher, Student)
- Real-time attendance tracking
- Subject management
- Attendance reports and analytics
- AI-powered chatbot using Gemini 1.5
- Modern and responsive UI

## Technologies Used

- Python 3.8+
- Flask
- AWS Rekognition
- Firebase
- Gemini AI
- Bootstrap 5
- jQuery

## Prerequisites

- Python 3.8 or higher
- AWS Account with Rekognition access
- Firebase project
- Gemini API key

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
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
```

Edit `.env` file with your credentials:
- AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION)
- Firebase credentials (FIREBASE_ADMIN_CREDENTIALS_BASE64)
- Gemini API key (GEMINI_API_KEY)

5. Initialize the database:
```bash
python create_admin.py
```

## Running the Application

1. Start the development server:
```bash
python run.py
```

2. Access the application at `http://localhost:5000`

## Deployment

The application is configured for deployment on Render. Follow these steps:

1. Create a new Web Service on Render
2. Connect your repository
3. Set the following:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn run:app`
4. Add environment variables in Render dashboard
5. Deploy

## Usage

1. Admin:
   - Manage users (create, edit, delete)
   - Manage subjects
   - View system-wide attendance statistics
   - Configure system settings

2. Teacher:
   - Mark attendance using face recognition
   - Manage attendance records
   - View attendance reports
   - Interact with AI assistant

3. Student:
   - Register face
   - View attendance records
   - Check attendance percentage
   - Get AI assistance

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

