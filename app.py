import os
import sys
import base64
import json
import io
import re
from datetime import datetime
import logging

import cv2
import numpy as np
from PIL import Image
from flask import Flask, request, jsonify, render_template, send_file
from flask_socketio import SocketIO, emit
import boto3
import firebase_admin
from firebase_admin import credentials, firestore
import google.generativeai as genai
import openpyxl
from openpyxl import Workbook

# -----------------------------
# 1) AWS Rekognition Setup
# -----------------------------
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
COLLECTION_ID = "students"

rekognition_client = boto3.client(
    'rekognition',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def create_collection_if_not_exists(collection_id):
    try:
        rekognition_client.create_collection(CollectionId=collection_id)
        logger.info(f"Collection '{collection_id}' created.")
    except rekognition_client.exceptions.ResourceAlreadyExistsException:
        logger.info(f"Collection '{collection_id}' already exists.")
    except Exception as e:
        logger.exception(f"Failed to create collection '{collection_id}': {e}")

# -----------------------------
# 2) Firebase Firestore Setup
# -----------------------------
base64_cred_str = os.getenv("FIREBASE_ADMIN_CREDENTIALS_BASE64")
if not base64_cred_str:
    raise ValueError("FIREBASE_ADMIN_CREDENTIALS_BASE64 not found in environment.")

decoded_cred_json = base64.b64decode(base64_cred_str)
cred_dict = json.loads(decoded_cred_json)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)
db = firestore.client()

# -----------------------------
# 3) Gemini Chatbot Setup
# -----------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

genai.configure(api_key=GEMINI_API_KEY)
# If you do NOT have access to "gemini-1.5-flash", switch to "models/chat-bison-001"
model = genai.GenerativeModel("models/gemini-1.5-flash")

# Chat memory
MAX_MEMORY = 20
conversation_memory = []

# A big system prompt describing the entire system
system_context = """You are Gemini, a somewhat witty (but polite) AI assistant.
Facial Recognition Attendance system features:

1) AWS Rekognition:
   - We keep a 'students' collection on startup.
   - /register indexes a face by (name + student_id).
   - /recognize detects faces in an uploaded image, logs attendance in Firestore if matched.

2) Attendance:
   - Firestore 'attendance' collection: { student_id, name, timestamp, subject_id, subject_name, status='PRESENT' }.
   - UI has tabs: Register, Recognize, Subjects, Attendance (Bootstrap + DataTables).
   - Attendance can filter, inline-edit, download/upload Excel.

3) Subjects:
   - We can add subjects to 'subjects' collection, referenced in recognition.

4) Multi-Face:
   - If multiple recognized faces, each is logged to attendance.

5) Chat:
   - You are the assistant, a bit humorous, guiding usage or code features.

Additionally, you have full access to Firebase Firestore and can perform CRUD operations on Subjects and Attendance records. You can provide real-time analytics and respond to system actions and errors.
"""

# Start the conversation with a system message
conversation_memory.append({"role": "system", "content": system_context})

# -----------------------------
# 4) Flask App Initialization
# -----------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure key
socketio = SocketIO(app, cors_allowed_origins="*")  # Allow all origins or specify your frontend URL

# -----------------------------
# 5) Logging Configuration
# -----------------------------
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to capture all types of log messages
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger()

# Initialize AWS Rekognition Collection
create_collection_if_not_exists(COLLECTION_ID)

# -----------------------------
# 6) Image Enhancement Function
# -----------------------------
def enhance_image(pil_image):
    """
    Enhance image quality to improve face detection in distant group photos.
    This includes increasing brightness and contrast.
    """
    # Convert PIL image to OpenCV format
    cv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    # Increase brightness and contrast
    alpha = 1.2  # Contrast control (1.0-3.0)
    beta = 30    # Brightness control (0-100)
    enhanced_cv_image = cv2.convertScaleAbs(cv_image, alpha=alpha, beta=beta)

    # Convert back to PIL Image
    enhanced_pil_image = Image.fromarray(cv2.cvtColor(enhanced_cv_image, cv2.COLOR_BGR2RGB))

    return enhanced_pil_image

# -----------------------------
# 7) Routes Definitions
# -----------------------------

# Root route to serve the main page
@app.route("/", methods=["GET"])
def index():
    logger.info("Root route '/' accessed")
    return render_template("index.html")

# Register Face (GET/POST)
@app.route("/register", methods=["GET", "POST"])
def register_face():
    if request.method == "GET":
        logger.info("/register route accessed via GET")
        return "Welcome to /register. Please POST with {name, student_id, image} to register."

    data = request.get_json()
    name = data.get('name')
    student_id = data.get('student_id')
    image = data.get('image')

    if not name or not student_id or not image:
        logger.warning("Missing name, student_id, or image in /register POST request")
        error_message = "Missing name, student_id, or image."
        socketio.emit('chat_message', {'message': error_message})
        return jsonify({"message": error_message}), 400

    sanitized_name = "".join(c if c.isalnum() or c in "_-." else "_" for c in name)
    try:
        image_data = image.split(",")[1]
    except IndexError:
        logger.error("Invalid image format in /register POST request")
        error_message = "Invalid image format."
        socketio.emit('chat_message', {'message': error_message})
        return jsonify({"message": error_message}), 400

    try:
        image_bytes = base64.b64decode(image_data)
    except base64.binascii.Error:
        logger.error("Invalid base64 encoding for image in /register POST request")
        error_message = "Invalid base64 encoding for image."
        socketio.emit('chat_message', {'message': error_message})
        return jsonify({"message": error_message}), 400

    try:
        pil_image = Image.open(io.BytesIO(image_bytes))
    except IOError:
        logger.error("Uploaded file is not a valid image in /register POST request")
        error_message = "Uploaded file is not a valid image."
        socketio.emit('chat_message', {'message': error_message})
        return jsonify({"message": error_message}), 400

    # Enhance image before indexing
    enhanced_image = enhance_image(pil_image)

    buffer = io.BytesIO()
    enhanced_image.save(buffer, format="JPEG")
    enhanced_image_bytes = buffer.getvalue()

    external_image_id = f"{sanitized_name}_{student_id}"
    try:
        response = rekognition_client.index_faces(
            CollectionId=COLLECTION_ID,
            Image={'Bytes': enhanced_image_bytes},
            ExternalImageId=external_image_id,
            DetectionAttributes=['ALL'],
            QualityFilter='AUTO'
        )
    except Exception as e:
        error_message = f"Failed to index face: {str(e)}"
        logger.exception(error_message)
        socketio.emit('chat_message', {'message': error_message})
        return jsonify({"message": error_message}), 500

    if not response.get('FaceRecords'):
        warning_message = "No face detected in the image."
        logger.warning(warning_message)
        socketio.emit('chat_message', {'message': warning_message})
        return jsonify({"message": warning_message}), 400

    success_message = f"Student {name} with ID {student_id} registered successfully!"
    logger.info(success_message)
    socketio.emit('chat_message', {'message': success_message})
    return jsonify({"message": success_message}), 200

# Recognize Face (GET/POST)
@app.route("/recognize", methods=["GET", "POST"])
def recognize_face():
    if request.method == "GET":
        logger.info("/recognize route accessed via GET")
        return "Welcome to /recognize. Please POST with {image, subject_id(optional)} to detect faces."

    data = request.get_json()
    image_str = data.get('image')
    subject_id = data.get('subject_id') or ""

    if not image_str:
        logger.warning("No image provided in /recognize POST request")
        error_message = "No image provided."
        socketio.emit('chat_message', {'message': error_message})
        return jsonify({"message": error_message}), 400

    # Optionally fetch subject name
    subject_name = ""
    if subject_id:
        try:
            sdoc = db.collection("subjects").document(subject_id).get()
            if sdoc.exists:
                subject_name = sdoc.to_dict().get("name", "")
            else:
                subject_name = "Unknown Subject"
        except Exception as e:
            logger.exception("Failed to fetch subject name in /recognize POST request")
            subject_name = "Unknown Subject"

    try:
        image_data = image_str.split(",")[1]
    except IndexError:
        logger.error("Invalid image format in /recognize POST request")
        error_message = "Invalid image format."
        socketio.emit('chat_message', {'message': error_message})
        return jsonify({"message": error_message}), 400

    try:
        image_bytes = base64.b64decode(image_data)
    except base64.binascii.Error:
        logger.error("Invalid base64 encoding for image in /recognize POST request")
        error_message = "Invalid base64 encoding for image."
        socketio.emit('chat_message', {'message': error_message})
        return jsonify({"message": error_message}), 400

    try:
        pil_image = Image.open(io.BytesIO(image_bytes))
    except IOError:
        logger.error("Uploaded file is not a valid image in /recognize POST request")
        error_message = "Uploaded file is not a valid image."
        socketio.emit('chat_message', {'message': error_message})
        return jsonify({"message": error_message}), 400

    # Enhance image before detection
    enhanced_image = enhance_image(pil_image)

    buffer = io.BytesIO()
    enhanced_image.save(buffer, format="JPEG")
    enhanced_image_bytes = buffer.getvalue()

    try:
        # Show progress via SocketIO
        socketio.emit('chat_message', {'message': "Face recognition in progress..."})
        detect_response = rekognition_client.detect_faces(
            Image={'Bytes': enhanced_image_bytes},
            Attributes=['ALL']
        )
    except Exception as e:
        error_message = f"Failed to detect faces: {str(e)}"
        logger.exception(error_message)
        socketio.emit('chat_message', {'message': error_message})
        return jsonify({"message": error_message}), 500

    faces = detect_response.get('FaceDetails', [])
    face_count = len(faces)
    identified_people = []

    if face_count == 0:
        no_faces_message = "No faces detected in the image."
        logger.info(no_faces_message)
        socketio.emit('chat_message', {'message': no_faces_message})
        return jsonify({
            "message": no_faces_message,
            "total_faces": face_count,
            "identified_people": identified_people
        }), 200

    for idx, face in enumerate(faces):
        bbox = face['BoundingBox']
        pil_img = Image.open(io.BytesIO(enhanced_image_bytes))
        img_width, img_height = pil_img.size

        left = int(bbox['Left'] * img_width)
        top = int(bbox['Top'] * img_height)
        width = int(bbox['Width'] * img_width)
        height = int(bbox['Height'] * img_height)
        right = left + width
        bottom = top + height

        # Crop the face from the image
        cropped_face = pil_img.crop((left, top, right, bottom))
        buffer = io.BytesIO()
        cropped_face.save(buffer, format="JPEG")
        cropped_face_bytes = buffer.getvalue()

        try:
            # Search for the face in the collection
            search_response = rekognition_client.search_faces_by_image(
                CollectionId=COLLECTION_ID,
                Image={'Bytes': cropped_face_bytes},
                MaxFaces=1,
                FaceMatchThreshold=60
            )
        except Exception as e:
            identified_people.append({
                "message": f"Error searching face {idx+1}: {str(e)}",
                "confidence": "N/A"
            })
            logger.exception(f"Error searching face {idx+1}")
            continue

        matches = search_response.get('FaceMatches', [])
        if not matches:
            identified_people.append({
                "message": "Face not recognized",
                "confidence": "N/A"
            })
            continue

        match = matches[0]
        ext_id = match['Face']['ExternalImageId']
        confidence = match['Face']['Confidence']

        parts = ext_id.split("_", 1)
        if len(parts) == 2:
            rec_name, rec_id = parts
        else:
            rec_name, rec_id = ext_id, "Unknown"

        identified_people.append({
            "name": rec_name,
            "student_id": rec_id,
            "confidence": confidence
        })

        # If recognized, log attendance
        if rec_id != "Unknown":
            doc = {
                "student_id": rec_id,
                "name": rec_name,
                "timestamp": datetime.utcnow().isoformat(),
                "subject_id": subject_id,
                "subject_name": subject_name,
                "status": "PRESENT"
            }
            try:
                db.collection("attendance").add(doc)
                success_message = f"Attendance recorded for {rec_name}."
                logger.info(success_message)
                socketio.emit('chat_message', {'message': success_message})
            except Exception as e:
                error_message = f"Failed to log attendance for {rec_id}: {str(e)}"
                logger.exception(error_message)
                socketio.emit('chat_message', {'message': error_message})

    final_message = f"{face_count} face(s) detected in the photo."
    logger.info(final_message)
    socketio.emit('chat_message', {'message': final_message})

    return jsonify({
        "message": final_message,
        "total_faces": face_count,
        "identified_people": identified_people
    }), 200

# SUBJECTS
@app.route("/api/subjects", methods=["GET", "POST", "PUT", "DELETE"])
def manage_subjects():
    if request.method == "GET":
        try:
            subjects = db.collection("subjects").stream()
            subj_list = [{"id": s.id, "name": s.to_dict().get("name", "")} for s in subjects]
            return jsonify({"subjects": subj_list}), 200
        except Exception as e:
            logger.exception("Failed to fetch subjects")
            return jsonify({"error": str(e)}), 500

    data = request.get_json()

    if request.method == "POST":
        subject_name = data.get("name")
        if not subject_name:
            return jsonify({"error": "Subject name is required"}), 400
        try:
            doc_ref = db.collection("subjects").add({"name": subject_name.strip(), "created_at": datetime.utcnow().isoformat()})
            success_message = f"Subject '{subject_name}' added successfully."
            logger.info(success_message)
            socketio.emit('chat_message', {'message': success_message})
            return jsonify({"message": success_message, "id": doc_ref[1].id}), 201
        except Exception as e:
            logger.exception("Failed to add subject")
            error_message = f"Failed to add subject: {str(e)}"
            socketio.emit('chat_message', {'message': error_message})
            return jsonify({"error": error_message}), 500

    elif request.method == "PUT":
        subject_id = data.get("id")
        new_name = data.get("name")
        if not subject_id or not new_name:
            return jsonify({"error": "Subject ID and new name are required"}), 400
        try:
            doc_ref = db.collection("subjects").document(subject_id)
            doc_ref.update({"name": new_name.strip()})
            success_message = f"Subject ID {subject_id} updated to '{new_name}'."
            logger.info(success_message)
            socketio.emit('chat_message', {'message': success_message})
            return jsonify({"message": "Subject updated successfully."}), 200
        except Exception as e:
            logger.exception("Failed to update subject")
            error_message = f"Failed to update subject: {str(e)}"
            socketio.emit('chat_message', {'message': error_message})
            return jsonify({"error": error_message}), 500

    elif request.method == "DELETE":
        subject_id = data.get("id")
        if not subject_id:
            return jsonify({"error": "Subject ID is required"}), 400
        try:
            db.collection("subjects").document(subject_id).delete()
            success_message = f"Subject ID {subject_id} deleted successfully."
            logger.info(success_message)
            socketio.emit('chat_message', {'message': success_message})
            return jsonify({"message": "Subject deleted successfully."}), 200
        except Exception as e:
            logger.exception("Failed to delete subject")
            error_message = f"Failed to delete subject: {str(e)}"
            socketio.emit('chat_message', {'message': error_message})
            return jsonify({"error": error_message}), 500

# ATTENDANCE
@app.route("/api/attendance/<action>", methods=["POST", "GET"])
def attendance_actions(action):
    if action == "add":
        data = request.get_json()
        try:
            db.collection("attendance").add({
                "student_id": data.get("student_id"),
                "name": data.get("name"),
                "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
                "subject_id": data.get("subject_id"),
                "subject_name": data.get("subject_name"),
                "status": data.get("status", "PRESENT")
            })
            success_message = f"Attendance recorded for student ID {data.get('student_id')}."
            logger.info(success_message)
            socketio.emit('chat_message', {'message': success_message})
            return jsonify({"message": "Attendance recorded successfully."}), 201
        except Exception as e:
            logger.exception("Failed to add attendance record")
            error_message = f"Failed to add attendance record: {str(e)}"
            socketio.emit('chat_message', {'message': error_message})
            return jsonify({"error": error_message}), 500

    elif action == "update":
        data = request.get_json()
        records = data.get("records", [])
        try:
            for rec in records:
                doc_id = rec.get("doc_id")
                if not doc_id:
                    continue
                ref = db.collection("attendance").document(doc_id)
                update_data = {k: v for k, v in rec.items() if k != "doc_id"}
                ref.update(update_data)
            success_message = f"Updated {len(records)} attendance records."
            logger.info(success_message)
            socketio.emit('chat_message', {'message': success_message})
            return jsonify({"message": "Attendance records updated successfully."}), 200
        except Exception as e:
            logger.exception("Failed to update attendance records")
            error_message = f"Failed to update attendance records: {str(e)}"
            socketio.emit('chat_message', {'message': error_message})
            return jsonify({"error": error_message}), 500

    elif action == "delete":
        data = request.get_json()
        record_ids = data.get("ids", [])
        try:
            for doc_id in record_ids:
                db.collection("attendance").document(doc_id).delete()
            success_message = f"Deleted {len(record_ids)} attendance records."
            logger.info(success_message)
            socketio.emit('chat_message', {'message': success_message})
            return jsonify({"message": "Attendance records deleted successfully."}), 200
        except Exception as e:
            logger.exception("Failed to delete attendance records")
            error_message = f"Failed to delete attendance records: {str(e)}"
            socketio.emit('chat_message', {'message': error_message})
            return jsonify({"error": error_message}), 500

    elif action == "get":
        # Implement filters similar to existing /api/attendance
        student_id = request.args.get("student_id")
        subject_id = request.args.get("subject_id")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        query = db.collection("attendance")
        if student_id:
            query = query.where("student_id", "==", student_id)
        if subject_id:
            query = query.where("subject_id", "==", subject_id)
        if start_date:
            try:
                dt_start = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.where("timestamp", ">=", dt_start.isoformat())
            except ValueError:
                logger.error("Invalid start_date format in /api/attendance/get GET request")
                error_message = "Invalid start_date format. Use YYYY-MM-DD."
                socketio.emit('chat_message', {'message': error_message})
                return jsonify({"error": error_message}), 400
        if end_date:
            try:
                dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59, microsecond=999999
                )
                query = query.where("timestamp", "<=", dt_end.isoformat())
            except ValueError:
                logger.error("Invalid end_date format in /api/attendance/get GET request")
                error_message = "Invalid end_date format. Use YYYY-MM-DD."
                socketio.emit('chat_message', {'message': error_message})
                return jsonify({"error": error_message}), 400

        try:
            results = query.stream()
            out_list = []
            for doc_ in results:
                dd = doc_.to_dict()
                dd["doc_id"] = doc_.id
                out_list.append(dd)
            logger.info(f"Fetched {len(out_list)} attendance records")
            return jsonify(out_list), 200
        except Exception as e:
            logger.exception("Failed to fetch attendance records")
            error_message = f"Failed to fetch attendance records: {str(e)}"
            socketio.emit('chat_message', {'message': error_message})
            return jsonify({"error": error_message}), 500

    # ATTENDANCE DOWNLOAD, UPLOAD, etc. can be similarly added as needed.

    # -----------------------------
    # 8) Gemini Chat Endpoint
    # -----------------------------
    @app.route("/process_prompt", methods=["POST"])
    def process_prompt():
        data = request.get_json()
        user_prompt = data.get("prompt", "").strip()
        if not user_prompt:
            logger.warning("No prompt provided in /process_prompt POST request")
            return jsonify({"error": "No prompt provided"}), 400

        # Add user message
        conversation_memory.append({"role": "user", "content": user_prompt})

        # Detect commands using regex
        add_subject_pattern = r"add subject (.+)"
        edit_subject_pattern = r"edit subject id (\w+) to (.+)"
        delete_subject_pattern = r"delete subject id (\w+)"
        # Add more patterns as needed

        response_message = ""

        if re.match(add_subject_pattern, user_prompt, re.IGNORECASE):
            subject_name = re.findall(add_subject_pattern, user_prompt, re.IGNORECASE)[0]
            # Call the manage_subjects_add function
            try:
                response = manage_subjects_add(subject_name)
                response_message = response.get("message", "Subject added successfully.")
            except Exception as e:
                response_message = f"Error adding subject: {str(e)}"

        elif re.match(edit_subject_pattern, user_prompt, re.IGNORECASE):
            matches = re.findall(edit_subject_pattern, user_prompt, re.IGNORECASE)
            if matches:
                subject_id, new_name = matches[0]
                try:
                    response = manage_subjects_edit(subject_id, new_name)
                    response_message = response.get("message", "Subject updated successfully.")
                except Exception as e:
                    response_message = f"Error editing subject: {str(e)}"
            else:
                response_message = "Invalid edit subject command format."

        elif re.match(delete_subject_pattern, user_prompt, re.IGNORECASE):
            subject_id = re.findall(delete_subject_pattern, user_prompt, re.IGNORECASE)[0]
            try:
                response = manage_subjects_delete(subject_id)
                response_message = response.get("message", "Subject deleted successfully.")
            except Exception as e:
                response_message = f"Error deleting subject: {str(e)}"

        else:
            # For non-command prompts, use Gemini to generate a response
            conv_str = ""
            for msg in conversation_memory:
                if msg["role"] == "system":
                    conv_str += f"System: {msg['content']}\n"
                elif msg["role"] == "user":
                    conv_str += f"User: {msg['content']}\n"
                else:
                    conv_str += f"Assistant: {msg['content']}\n"

            try:
                response = model.generate_content(conv_str)
            except Exception as e:
                response_message = f"Error generating response: {str(e)}"
                logger.exception("Failed to generate response from Gemini Chatbot")
            else:
                if not response.candidates:
                    response_message = "Hmm, I'm having trouble responding right now."
                else:
                    parts = response.candidates[0].content.parts
                    response_message = "".join(part.text for part in parts).strip()

        # Add assistant reply
        conversation_memory.append({"role": "assistant", "content": response_message})

        if len(conversation_memory) > MAX_MEMORY:
            conversation_memory.pop(0)

        # Emit the response message to the frontend via SocketIO
        socketio.emit('chat_message', {'message': response_message})

        logger.info(f"Gemini Chatbot response: {response_message}")
        return jsonify({"message": response_message}), 200

    def manage_subjects_add(subject_name):
        # Simulate POST request to /api/subjects
        with app.test_request_context("/api/subjects", method="POST", json={"name": subject_name}):
            return manage_subjects()

    def manage_subjects_edit(subject_id, new_name):
        # Simulate PUT request to /api/subjects
        with app.test_request_context("/api/subjects", method="PUT", json={"id": subject_id, "name": new_name}):
            return manage_subjects()

    def manage_subjects_delete(subject_id):
        # Simulate DELETE request to /api/subjects
        with app.test_request_context("/api/subjects", method="DELETE", json={"id": subject_id}):
            return manage_subjects()

    # Handle favicon.ico to prevent 404 errors
    @app.route("/favicon.ico")
    def favicon():
        logger.info("Favicon request received")
        return send_file(io.BytesIO(), mimetype='image/vnd.microsoft.icon')

    # Handle 404 errors by serving the index page (useful for single-page applications)
    @app.errorhandler(404)
    def not_found(e):
        logger.warning(f"404 error: {request.path}")
        socketio.emit('chat_message', {'message': f"Page {request.path} not found. Redirecting to home."})
        return render_template("index.html"), 200

    # -----------------------------
    # 9) Run App
    # -----------------------------
    if __name__ == "__main__":
        port = int(os.getenv("PORT", 5000))
        logger.info(f"Starting Flask app on port {port}")
        socketio.run(app, host="0.0.0.0", port=port, debug=True)
    ```

**Key Features Implemented:**

1. **AWS Rekognition Integration:**
   - Registers and recognizes faces using AWS Rekognition.
   - Enhances images before processing to improve accuracy.
   
2. **Firebase Firestore Integration:**
   - Performs CRUD operations on `subjects` and `attendance` collections.
   - Logs attendance records upon successful face recognition.

3. **Gemini Chatbot Integration:**
   - Parses user commands to perform CRUD operations.
   - Provides real-time feedback and notifications via the chatbot interface.

4. **Real-Time Communication:**
   - Utilizes Flask-SocketIO for real-time interactions between backend and frontend.
   - Emits messages to the frontend to inform users about system actions and errors.

5. **Error Handling:**
   - Comprehensive error handling with detailed logging.
   - Notifies users of errors through the chatbot interface.

---

## **5. `templates/index.html`**

The main frontend HTML file with structured tabs, progress bars, and chatbot integration.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Facial Recognition Attendance + Gemini Chat</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <!-- Bootstrap CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
  <!-- DataTables CSS -->
  <link rel="stylesheet" href="https://cdn.datatables.net/1.13.4/css/jquery.dataTables.min.css">
  <!-- SocketIO -->
  <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"
          integrity="sha384-fM1QdWWjBOB4vq9W7HAJcqTq8+Sn1lkFwVvL1LldPN5rocttWc9Qo8S0vK23/KRG"
          crossorigin="anonymous"></script>
  <!-- Custom CSS -->
  <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
</head>
<body class="container">

<h1 class="my-4">Facial Recognition Attendance + Gemini Chat</h1>

<!-- Nav Tabs -->
<ul class="nav nav-tabs" id="mainTabs" role="tablist">
  <li class="nav-item">
    <button class="nav-link active" id="register-tab" data-bs-toggle="tab" data-bs-target="#register" type="button" role="tab">
      Register
    </button>
  </li>
  <li class="nav-item">
    <button class="nav-link" id="recognize-tab" data-bs-toggle="tab" data-bs-target="#recognize" type="button" role="tab">
      Recognize
    </button>
  </li>
  <li class="nav-item">
    <button class="nav-link" id="subjects-tab" data-bs-toggle="tab" data-bs-target="#subjects" type="button" role="tab">
      Subjects
    </button>
  </li>
  <li class="nav-item">
    <button class="nav-link" id="attendance-tab" data-bs-toggle="tab" data-bs-target="#attendance" type="button" role="tab">
      Attendance
    </button>
  </li>
</ul>

<div class="tab-content" id="mainTabContent">
  <!-- REGISTER -->
  <div class="tab-pane fade show active mt-4" id="register" role="tabpanel" aria-labelledby="register-tab">
    <h3>Register a Face</h3>
    <label class="form-label">Name</label>
    <input type="text" id="reg_name" class="form-control" placeholder="Enter Name" />
    <label class="form-label">Student ID</label>
    <input type="text" id="reg_student_id" class="form-control" placeholder="Enter Student ID" />
    <label class="form-label">Image</label>
    <input type="file" id="reg_image" class="form-control" accept="image/*" />
    <button onclick="registerFace()" class="btn btn-primary mt-2">Register</button>
    <div id="register_result" class="alert alert-info mt-3" style="display:none;"></div>
  </div>

  <!-- RECOGNIZE -->
  <div class="tab-pane fade mt-4" id="recognize" role="tabpanel" aria-labelledby="recognize-tab">
    <h3>Recognize Faces</h3>
    <label class="form-label">Subject (optional)</label>
    <select id="rec_subject_select" class="form-control mb-2">
      <option value="">-- No Subject --</option>
    </select>
    <label class="form-label">Image</label>
    <input type="file" id="rec_image" class="form-control" accept="image/*" />
    <button onclick="recognizeFace()" class="btn btn-success mt-2">Recognize</button>
    
    <!-- Progress Bar -->
    <div id="recognitionProgress" class="progress mt-3" style="display:none;">
      <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" aria-valuenow="100"
           aria-valuemin="0" aria-valuemax="100" style="width: 100%"></div>
    </div>
    
    <div id="recognize_result" class="alert alert-info mt-3" style="display:none;"></div>
    <div id="identified_faces" class="mt-3"></div>
  </div>

  <!-- SUBJECTS -->
  <div class="tab-pane fade mt-4" id="subjects" role="tabpanel" aria-labelledby="subjects-tab">
    <h3>Manage Subjects</h3>
    <label class="form-label">New Subject Name:</label>
    <input type="text" id="subject_name" class="form-control" placeholder="e.g. Mathematics" />
    <button onclick="addSubject()" class="btn btn-primary mt-2">Add Subject</button>
    <div id="subject_result" class="alert alert-info mt-3" style="display:none;"></div>
    <hr />
    <h5>Existing Subjects</h5>
    <ul id="subjects_list"></ul>
  </div>

  <!-- ATTENDANCE -->
  <div class="tab-pane fade mt-4" id="attendance" role="tabpanel" aria-labelledby="attendance-tab">
    <h3>Attendance Records</h3>
    <div class="row mb-3">
      <div class="col-md-3">
        <label class="form-label">Student ID</label>
        <input type="text" id="filter_student_id" class="form-control" placeholder="e.g. 1234" />
      </div>
      <div class="col-md-3">
        <label class="form-label">Subject ID</label>
        <input type="text" id="filter_subject_id" class="form-control" placeholder="e.g. abc123" />
      </div>
      <div class="col-md-3">
        <label class="form-label">Start Date</label>
        <input type="date" id="filter_start" class="form-control" />
      </div>
      <div class="col-md-3">
        <label class="form-label">End Date</label>
        <input type="date" id="filter_end" class="form-control" />
      </div>
    </div>
    <button class="btn btn-info mb-3" onclick="loadAttendance()">Apply Filters</button>
    <table id="attendanceTable" class="display table table-striped w-100">
      <thead>
        <tr>
          <th>Doc ID</th>
          <th>Student ID</th>
          <th>Name</th>
          <th>Subject ID</th>
          <th>Subject Name</th>
          <th>Timestamp</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
    <div class="mt-3">
      <button class="btn btn-warning" onclick="saveEdits()">Save Changes</button>
      <button class="btn btn-secondary" onclick="downloadExcel()">Download Excel</button>
      <button class="btn btn-link" onclick="downloadTemplate()">Download Template</button>
      <label class="form-label d-block mt-3">Upload Excel (template must match columns):</label>
      <input type="file" id="excelFile" accept=".xlsx" class="form-control mb-2" />
      <button class="btn btn-dark" onclick="uploadExcel()">Upload Excel</button>
    </div>
  </div>
</div>

<!-- Chatbot Toggle Button -->
<button id="chatbotToggle">💬</button>

<!-- Chatbot Window -->
<div id="chatbotWindow" style="display:none; flex-direction:column;">
  <div id="chatHeader">
    <span>Gemini Chat</span>
    <button class="close-btn" id="chatCloseBtn">X</button>
  </div>
  <div id="chatMessages" style="flex:1; overflow-y:auto; padding:10px; font-size:14px;"></div>
  <div id="chatInputArea" style="display:flex; border-top:1px solid #ddd;">
    <input type="text" id="chatInput" placeholder="Type a message..." style="flex:1; padding:8px; border:none; outline:none; font-size:14px;" />
    <button id="chatSendBtn" style="background-color:#0d6efd; color:#fff; border:none; padding:0 15px; cursor:pointer;">Send</button>
  </div>
</div>

<!-- Scripts -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
<!-- Custom JS -->
<script src="{{ url_for('static', filename='js/scripts.js') }}"></script>
</body>
</html>
