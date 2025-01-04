# Face Recognition Project for Render

This project uses AWS Rekognition to register and recognize faces. It is designed to run on the Render platform.

## Running the Project on Render

1. **Set Up Environment Variables**:
   - Add the following environment variables in Render:
     - `AWS_ACCESS_KEY_ID`: Your AWS access key.
     - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key.
     - `AWS_REGION`: The AWS region for Rekognition (e.g., `us-east-1`).
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
   - Use the "Register" feature to register a student's face with their name and ID.
   - Use the "Recognize" feature to identify a face and retrieve the corresponding name and ID.

## File Structure

- `app.py`: Flask backend for face registration and recognition.
- `templates/index.html`: Frontend interface for interacting with the app.
- `static/script.js`: JavaScript for handling image uploads and API calls.
- `requirements.txt`: List of Python dependencies.

## Important Notes

Ensure your AWS IAM user has the necessary permissions for Rekognition and that the collection is created before deploying.

