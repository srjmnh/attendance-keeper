# Attendance Keeper

A facial recognition-based attendance management system built with Flask, AWS Rekognition, and Firebase.

## Features

- Face-based attendance tracking using AWS Rekognition
- Real-time data storage with Firebase Firestore
- Role-based access control (Admin, Teacher, Student)
- Subject management
- Attendance reports with Excel export/import
- AI-powered chat assistance using Google's Gemini
- Modern, responsive UI

## Prerequisites

- Python 3.8+
- AWS Account with Rekognition access
- Firebase Project
- Google Cloud Project (for Gemini API)

## Environment Variables

```bash
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=your_aws_region
FIREBASE_ADMIN_CREDENTIALS_BASE64=your_base64_encoded_firebase_credentials
GEMINI_API_KEY=your_gemini_api_key
SECRET_KEY=your_flask_secret_key
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

4. Set up environment variables (see above section)

5. Run the application:
```bash
python app.py
```

## Default Admin Account

Username: admin
Password: Admin123!

**Important**: Change the default password immediately after first login.

## License

MIT License

