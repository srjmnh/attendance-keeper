# Facial Recognition Attendance System

This project utilizes AWS Rekognition to register and recognize faces, integrated with Firebase Firestore for data management and Gemini Chatbot for interactive assistance. It's designed to run on the Render platform.

## Running the Project on Render

1. **Set Up Environment Variables**:
   - Add the following environment variables in Render:
     - `AWS_ACCESS_KEY_ID`: Your AWS access key.
     - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key.
     - `AWS_REGION`: The AWS region for Rekognition (e.g., `us-east-1`).
     - `FIREBASE_ADMIN_CREDENTIALS_BASE64`: Base64 encoded Firebase credentials JSON.
     - `GEMINI_API_KEY`: Your Gemini API key.
     - `SECRET_KEY`: A secret key for Flask sessions.
   - Ensure your Rekognition collection is named `students`.

2. **Deploy the Application**:
   - Upload this repository to a GitHub repository or zip it for direct upload.
   - In Render, create a new web service.
     - Choose the repository or upload the zip file.
     - Select `Python` as the runtime.
     - Set the **Start Command** to `python app.py`.

3. **Dependencies**:
   - Render will automatically install the dependencies listed in `requirements.txt`.

4. **Usage**:
   - Navigate to the deployed application.
   - **Login** as an existing user or use the admin panel to create new users.
   - Use the "Register" feature to register a student's face with their name and ID.
   - Use the "Recognize" feature to identify a face and retrieve the corresponding name and ID.
   - Manage subjects and attendance records through the respective tabs.
   - Utilize the Gemini Chatbot for assistance and guidance.

## File Structure

- `app.py`: Flask backend for face registration, recognition, user management, and integrating with AWS Rekognition, Firebase Firestore, and Gemini Chatbot.
- `templates/dashboard.html`: Frontend interface for interacting with the app.
- `templates/login.html`: User login interface.
- `templates/admin_panel.html`: Admin panel for user management.
- `templates/base.html`: Base template that other templates extend.
- `static/script.js`: JavaScript for handling image uploads and API calls.
- `static/css/styles.css`: Custom CSS styles.
- `requirements.txt`: List of Python dependencies.
- `README.md`: Project documentation.

## Important Notes

- Ensure your AWS IAM user has the necessary permissions for Rekognition.
- The Firestore collections used:
  - `users`: To store user information.
  - `subjects`: To manage subjects.
  - `attendance`: To log attendance records.
- The Rekognition collection should be created as `students` before deploying.
- The Gemini Chatbot requires a valid API key and proper configuration.

## Troubleshooting

- **Missing Environment Variables**: Ensure all required environment variables are set in Render.
- **AWS Rekognition Issues**: Verify that the AWS credentials have the correct permissions and that the `students` collection exists.
- **Firebase Firestore Errors**: Check that the Firebase credentials are correctly provided and that Firestore is properly initialized.
- **Gemini Chatbot Not Responding**: Ensure the `GEMINI_API_KEY` is valid and that the model name is correct.

## License

This project is licensed under the [MIT License](LICENSE).

---

