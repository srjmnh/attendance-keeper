import os
import base64
import json
import io
from datetime import datetime

from flask import Flask, request, jsonify, render_template, send_file
import boto3
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image
import openpyxl
from openpyxl import Workbook
import google.generativeai as genai
from dotenv import load_dotenv
import logging
from flask_cors import CORS
import cv2
import numpy as np

# -----------------------------
# 1) Initialize Flask App
# -----------------------------
app = Flask(__name__)
CORS(app)  # Enable CORS if frontend is served from a different origin

# -----------------------------
# 2) Setup Logging
# -----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# 3) Load Environment Variables
# -----------------------------
load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
COLLECTION_ID = "students"

FIREBASE_ADMIN_CREDENTIALS_BASE64 = os.getenv('FIREBASE_ADMIN_CREDENTIALS_BASE64')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
PORT = int(os.getenv('PORT', 5000))

if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, FIREBASE_ADMIN_CREDENTIALS_BASE64, GEMINI_API_KEY]):
    logger.error("One or more required environment variables are missing.")
    raise EnvironmentError("One or more required environment variables are missing.")

# -----------------------------
# 4) Initialize Firebase Firestore
# -----------------------------
try:
    decoded_cred_json = base64.b64decode(FIREBASE_ADMIN_CREDENTIALS_BASE64)
    cred_dict = json.loads(decoded_cred_json)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    logger.info("Initialized Firebase Firestore.")
except Exception as e:
    logger.error(f"Failed to initialize Firebase: {e}")
    raise e

# -----------------------------
# 5) Initialize AWS Rekognition Client
# -----------------------------
try:
    rekognition_client = boto3.client(
        'rekognition',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
    logger.info("Initialized AWS Rekognition client.")
except Exception as e:
    logger.error(f"Failed to initialize AWS Rekognition client: {e}")
    raise e

def create_collection_if_not_exists(collection_id):
    try:
        rekognition_client.create_collection(CollectionId=collection_id)
        logger.info(f"Collection '{collection_id}' created.")
    except rekognition_client.exceptions.ResourceAlreadyExistsException:
        logger.info(f"Collection '{collection_id}' already exists.")
    except Exception as e:
        logger.error(f"Error creating collection '{collection_id}': {e}")

create_collection_if_not_exists(COLLECTION_ID)

# -----------------------------
# 6) Initialize Gemini Chatbot
# -----------------------------
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("models/gemini-1.5-flash")  # Use the appropriate model
    logger.info("Initialized Gemini Chatbot.")
except Exception as e:
    logger.error(f"Failed to initialize Gemini Chatbot: {e}")
    raise e

# Chat memory
MAX_MEMORY = 20
conversation_memory = []

# System context for Gemini
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
   - You have full access to Firebase Firestore to perform operations like adding, editing, deleting subjects, and accessing analytics.
"""

# Start the conversation with a system message
conversation_memory.append({"role": "system", "content": system_context})

# -----------------------------
# 7) Image Enhancement Functions
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

def upscale_image(image_bytes, upscale_factor=2):
    """Super-resolution (optional)."""
    image = Image.open(io.BytesIO(image_bytes))
    width, height = image.size
    upscaled_image = image.resize((width * upscale_factor, height * upscale_factor), Image.ANTIALIAS)
    buffer = io.BytesIO()
    upscaled_image.save(buffer, format="JPEG")
    return buffer.getvalue()

def denoise_image(image_bytes):
    """Noise reduction (optional)."""
    image = Image.open(io.BytesIO(image_bytes))
    image_array = np.array(image)
    denoised = cv2.fastNlMeansDenoisingColored(image_array, None, 10, 10, 7, 21)
    denoised_image = Image.fromarray(denoised)
    buffer = io.BytesIO()
    denoised_image.save(buffer, format="JPEG")
    return buffer.getvalue()

def equalize_image(image_bytes):
    """Histogram equalization (optional)."""
    image = Image.open(io.BytesIO(image_bytes))
    image_array = np.array(image)
    lab = cv2.cvtColor(image_array, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.equalizeHist(l)
    lab = cv2.merge((l, a, b))
    eq_image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    eq_image_pil = Image.fromarray(eq_image)
    buffer = io.BytesIO()
    eq_image_pil.save(buffer, format="JPEG")
    return buffer.getvalue()

def split_image(pil_image, grid_size=3):
    """Split PIL image into grid_size x grid_size smaller regions."""
    width, height = pil_image.size
    region_width = width // grid_size
    region_height = height // grid_size
    regions = []
    for row in range(grid_size):
        for col in range(grid_size):
            left = col * region_width
            top = row * region_height
            right = (col + 1) * region_width
            bottom = (row + 1) * region_height
            regions.append(pil_image.crop((left, top, right, bottom)))
    return regions

# -----------------------------
# 8) Event Logging Functions
# -----------------------------
def log_event(action, details=""):
    """
    Logs an event and notifies the chatbot.
    """
    message = f"Action: {action}. Details: {details}"
    conversation_memory.append({"role":"assistant","content":message})
    if len(conversation_memory) > MAX_MEMORY:
        conversation_memory.pop(0)
    logger.info(message)

def log_error(error_message, context=""):
    """
    Logs an error and notifies the chatbot.
    """
    message = f"Error: {error_message}. Context: {context}"
    conversation_memory.append({"role":"assistant","content":message})
    if len(conversation_memory) > MAX_MEMORY:
        conversation_memory.pop(0)
    logger.error(message)

# -----------------------------
# 9) API Endpoints for Firebase Operations
# -----------------------------

@app.route("/api/subjects/add", methods=["POST"])
def api_add_subject():
    data = request.json
    subject_name = data.get("subject_name")
    if not subject_name:
        log_error("No subject_name provided", "Add Subject API")
        return jsonify({"error": "No subject_name provided"}), 400
    try:
        doc_ref = db.collection("subjects").document()
        doc_ref.set({
            "name": subject_name.strip(),
            "created_at": datetime.utcnow().isoformat()
        })
        log_event("Added a new subject", f"Subject Name: {subject_name}")
        return jsonify({"message": f"Subject '{subject_name}' added successfully!", "subject_id": doc_ref.id}), 200
    except Exception as e:
        log_error(f"Failed to add subject: {str(e)}", "Add Subject API")
        return jsonify({"error": f"Failed to add subject: {str(e)}"}), 500

@app.route("/api/subjects/edit", methods=["POST"])
def api_edit_subject():
    data = request.json
    subject_id = data.get("subject_id")
    new_name = data.get("new_name")
    if not subject_id or not new_name:
        log_error("subject_id and new_name are required", "Edit Subject API")
        return jsonify({"error": "subject_id and new_name are required"}), 400
    try:
        doc_ref = db.collection("subjects").document(subject_id)
        doc = doc_ref.get()
        if not doc.exists:
            log_error("Subject not found", "Edit Subject API")
            return jsonify({"error": "Subject not found"}), 404
        doc_ref.update({"name": new_name.strip()})
        log_event("Edited a subject", f"Subject ID: {subject_id}, New Name: {new_name}")
        return jsonify({"message": f"Subject '{subject_id}' updated successfully!", "new_name": new_name}), 200
    except Exception as e:
        log_error(f"Failed to edit subject: {str(e)}", "Edit Subject API")
        return jsonify({"error": f"Failed to edit subject: {str(e)}"}), 500

@app.route("/api/subjects/delete", methods=["POST"])
def api_delete_subject():
    data = request.json
    subject_id = data.get("subject_id")
    if not subject_id:
        log_error("subject_id is required", "Delete Subject API")
        return jsonify({"error": "subject_id is required"}), 400
    try:
        doc_ref = db.collection("subjects").document(subject_id)
        doc = doc_ref.get()
        if not doc.exists:
            log_error("Subject not found", "Delete Subject API")
            return jsonify({"error": "Subject not found"}), 404
        doc_ref.delete()
        log_event("Deleted a subject", f"Subject ID: {subject_id}")
        return jsonify({"message": f"Subject '{subject_id}' deleted successfully!"}), 200
    except Exception as e:
        log_error(f"Failed to delete subject: {str(e)}", "Delete Subject API")
        return jsonify({"error": f"Failed to delete subject: {str(e)}"}), 500

@app.route("/api/subjects/get", methods=["GET"])
def get_subjects():
    try:
        subjects = db.collection("subjects").stream()
        subj_list = []
        for subject in subjects:
            subj_data = subject.to_dict()
            subj_list.append({"id": subject.id, "name": subj_data.get("name", "")})
        log_event("Fetched subjects", f"Number of subjects fetched: {len(subj_list)}")
        return jsonify({"subjects": subj_list}), 200
    except Exception as e:
        log_error(f"Failed to fetch subjects: {str(e)}", "Get Subjects API")
        return jsonify({"error": f"Failed to fetch subjects: {str(e)}"}), 500

@app.route("/api/analytics", methods=["GET"])
def api_get_analytics():
    try:
        # Example analytics: Total Attendance per Subject
        subjects = db.collection("subjects").stream()
        analytics = {}
        for subject in subjects:
            subject_id = subject.id
            subject_name = subject.to_dict().get("name", "Unknown")
            attendance = db.collection("attendance").where("subject_id", "==", subject_id).stream()
            count = sum(1 for _ in attendance)
            analytics[subject_name] = count
        log_event("Fetched analytics data", "Total Attendance per Subject")
        return jsonify({"analytics": analytics}), 200
    except Exception as e:
        log_error(f"Failed to fetch analytics: {str(e)}", "Analytics API")
        return jsonify({"error": f"Failed to fetch analytics: {str(e)}"}), 500

# -----------------------------
# 10) Attendance Endpoints
# -----------------------------

@app.route("/api/attendance", methods=["GET"])
def get_attendance():
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
            return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD."}), 400
    if end_date:
        try:
            dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            query = query.where("timestamp", "<=", dt_end.isoformat())
        except ValueError:
            return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD."}), 400

    try:
        results = query.stream()
        out_list = []
        for doc_ in results:
            dd = doc_.to_dict()
            dd["doc_id"] = doc_.id
            out_list.append(dd)
        log_event("Fetched attendance records", f"Number of records fetched: {len(out_list)}")
        return jsonify(out_list)
    except Exception as e:
        log_error(f"Failed to fetch attendance records: {str(e)}", "Get Attendance API")
        return jsonify({"error": f"Failed to fetch attendance records: {str(e)}"}), 500

@app.route("/api/attendance/update", methods=["POST"])
def update_attendance():
    data = request.json
    records = data.get("records", [])
    try:
        for rec in records:
            doc_id = rec.get("doc_id")
            if not doc_id:
                continue
            ref = db.collection("attendance").document(doc_id)
            update_data = {
                "student_id": rec.get("student_id",""),
                "name": rec.get("name",""),
                "subject_id": rec.get("subject_id",""),
                "subject_name": rec.get("subject_name",""),
                "timestamp": rec.get("timestamp",""),
                "status": rec.get("status","")
            }
            ref.update(update_data)
        log_event("Updated attendance records", f"Number of records updated: {len(records)}")
        return jsonify({"message": "Attendance records updated successfully."}), 200
    except Exception as e:
        log_error(f"Failed to update attendance records: {str(e)}", "Update Attendance API")
        return jsonify({"error": f"Failed to update attendance records: {str(e)}"}), 500

@app.route("/api/attendance/download", methods=["GET"])
def download_attendance_excel():
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
            return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD."}), 400
    if end_date:
        try:
            dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            query = query.where("timestamp", "<=", dt_end.isoformat())
        except ValueError:
            return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD."}), 400

    try:
        results = query.stream()
        att_list = []
        for doc_ in results:
            dd = doc_.to_dict()
            dd["doc_id"] = doc_.id
            att_list.append(dd)

        wb = Workbook()
        ws = wb.active
        ws.title = "Attendance"
        headers = ["doc_id", "student_id", "name", "subject_id", "subject_name", "timestamp", "status"]
        ws.append(headers)

        for record in att_list:
            row = [
                record.get("doc_id",""),
                record.get("student_id",""),
                record.get("name",""),
                record.get("subject_id",""),
                record.get("subject_name",""),
                record.get("timestamp",""),
                record.get("status","")
            ]
            ws.append(row)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        log_event("Downloaded attendance as Excel", f"Number of records: {len(att_list)}")
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="attendance.xlsx"
        )
    except Exception as e:
        log_error(f"Failed to download Excel: {str(e)}", "Download Attendance API")
        return jsonify({"error": f"Failed to download Excel: {str(e)}"}), 500

@app.route("/api/attendance/template", methods=["GET"])
def download_template():
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Attendance Template"
        headers = ["doc_id","student_id","name","subject_id","subject_name","timestamp","status"]
        ws.append(headers)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        log_event("Downloaded attendance template", "Template downloaded")
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="attendance_template.xlsx"
        )
    except Exception as e:
        log_error(f"Failed to download template: {str(e)}", "Download Template API")
        return jsonify({"error": f"Failed to download template: {str(e)}"}), 500

@app.route("/api/attendance/upload", methods=["POST"])
def upload_attendance_excel():
    try:
        if "file" not in request.files:
            log_error("No file uploaded", "Upload Attendance API")
            return jsonify({"error": "No file uploaded"}), 400
        file = request.files["file"]
        if not file.filename.endswith(".xlsx"):
            log_error("Uploaded file is not an .xlsx", "Upload Attendance API")
            return jsonify({"error": "Please upload a .xlsx file"}), 400

        wb = openpyxl.load_workbook(file)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        expected = ("doc_id","student_id","name","subject_id","subject_name","timestamp","status")
        if not rows or rows[0] != expected:
            log_error("Incorrect template format", "Upload Attendance API")
            return jsonify({"error": "Incorrect template format"}), 400

        try:
            for row in rows[1:]:
                doc_id, student_id, name, subject_id, subject_name, timestamp, status = row
                if doc_id:
                    doc_data = {
                        "student_id": student_id or "",
                        "name": name or "",
                        "subject_id": subject_id or "",
                        "subject_name": subject_name or "",
                        "timestamp": timestamp or "",
                        "status": status or ""
                    }
                    db.collection("attendance").document(doc_id).set(doc_data, merge=True)
                else:
                    new_doc = {
                        "student_id": student_id or "",
                        "name": name or "",
                        "subject_id": subject_id or "",
                        "subject_name": subject_name or "",
                        "timestamp": timestamp or "",
                        "status": status or ""
                    }
                    db.collection("attendance").add(new_doc)
            log_event("Uploaded attendance from Excel", f"Number of records imported: {len(rows)-1}")
            return jsonify({"message": "Excel data imported successfully."}), 200
        except Exception as e:
            log_error(f"Failed to import Excel data: {str(e)}", "Upload Attendance API")
            return jsonify({"error": f"Failed to import Excel data: {str(e)}"}), 500
    except Exception as e:
        log_error(f"Failed to process upload: {str(e)}", "Upload Attendance API")
        return jsonify({"error": f"Failed to process upload: {str(e)}"}), 500

# -----------------------------
# 11) Register Face (GET/POST)
# -----------------------------
@app.route("/register", methods=["GET","POST"])
def register_face():
    if request.method == "GET":
        return "Welcome to /register. Please POST with {name, student_id, image} to register.", 200

    data = request.json
    name = data.get('name')
    student_id = data.get('student_id')
    image = data.get('image')
    if not name or not student_id or not image:
        log_error("Missing name, student_id, or image", "Register Route")
        return jsonify({"message": "Missing name, student_id, or image"}), 400

    sanitized_name = "".join(c if c.isalnum() or c in "_-." else "_" for c in name)
    try:
        image_data = image.split(",")[1]
    except IndexError:
        log_error("Invalid image format", "Register Route")
        return jsonify({"message": "Invalid image format"}), 400

    try:
        image_bytes = base64.b64decode(image_data)
    except base64.binascii.Error:
        log_error("Invalid base64 encoding for image", "Register Route")
        return jsonify({"message": "Invalid base64 encoding for image"}), 400

    try:
        pil_image = Image.open(io.BytesIO(image_bytes))
    except IOError:
        log_error("Uploaded file is not a valid image", "Register Route")
        return jsonify({"message": "Uploaded file is not a valid image"}), 400

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
        log_error(f"Failed to index face: {str(e)}", "Register Route")
        return jsonify({"message": f"Failed to index face: {str(e)}"}), 500

    if not response.get('FaceRecords'):
        log_error("No face detected in the image", "Register Route")
        return jsonify({"message": "No face detected in the image"}), 400

    log_event("Registered a new face", f"Name: {name}, Student ID: {student_id}")
    return jsonify({"message": f"Student {name} with ID {student_id} registered successfully!"}), 200

# -----------------------------
# 12) Recognize Face (GET/POST)
# -----------------------------
@app.route("/recognize", methods=["GET","POST"])
def recognize_face():
    if request.method == "GET":
        return "Welcome to /recognize. Please POST with {image, subject_id(optional)} to detect faces.", 200

    data = request.json
    image_str = data.get('image')
    subject_id = data.get('subject_id') or ""
    if not image_str:
        log_error("No image provided", "Recognize Route")
        return jsonify({"message": "No image provided"}), 400

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
            log_error(f"Failed to fetch subject name: {e}", "Recognize Route")
            subject_name = "Unknown Subject"

    try:
        image_data = image_str.split(",")[1]
    except IndexError:
        log_error("Invalid image format", "Recognize Route")
        return jsonify({"message": "Invalid image format"}), 400

    try:
        image_bytes = base64.b64decode(image_data)
    except base64.binascii.Error:
        log_error("Invalid base64 encoding for image", "Recognize Route")
        return jsonify({"message": "Invalid base64 encoding for image"}), 400

    try:
        pil_image = Image.open(io.BytesIO(image_bytes))
    except IOError:
        log_error("Uploaded file is not a valid image", "Recognize Route")
        return jsonify({"message": "Uploaded file is not a valid image"}), 400

    # Enhance image before detection
    enhanced_image = enhance_image(pil_image)

    buffer = io.BytesIO()
    enhanced_image.save(buffer, format="JPEG")
    enhanced_image_bytes = buffer.getvalue()

    try:
        # Detect faces in the image
        detect_response = rekognition_client.detect_faces(
            Image={'Bytes': enhanced_image_bytes},
            Attributes=['ALL']
        )
    except Exception as e:
        log_error(f"Failed to detect faces: {str(e)}", "Recognize Route")
        return jsonify({"message": f"Failed to detect faces: {str(e)}"}), 500

    faces = detect_response.get('FaceDetails', [])
    face_count = len(faces)
    identified_people = []

    if face_count == 0:
        log_event("No faces detected during recognition", f"Subject ID: {subject_id}")
        return jsonify({
            "message": "No faces detected in the image.",
            "total_faces": face_count,
            "identified_people": identified_people
        }), 200

    for idx, face in enumerate(faces):
        # Rekognition provides bounding box coordinates relative to image dimensions
        bbox = face['BoundingBox']
        pil_img = Image.open(io.BytesIO(enhanced_image_bytes))
        img_width, img_height = pil_img.size

        left = int(bbox['Left'] * img_width)
        top = int(bbox['Top'] * img_height)
        width = int(bbox['Width'] * img_width)
        height = int(bbox['Height'] * img_height)
        right = left + width
        bottom = int((bbox['Top'] + bbox['Height']) * img_height)  # Ensure bottom is in height coords

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
            log_error(f"Error searching face {idx+1}: {str(e)}", "Recognize Route")
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
                log_event("Logged attendance", f"Student ID: {rec_id}, Subject ID: {subject_id}")
            except Exception as e:
                log_error(f"Failed to log attendance for {rec_id}: {str(e)}", "Recognize Route")

    return jsonify({
        "message": f"{face_count} face(s) detected in the photo.",
        "total_faces": face_count,
        "identified_people": identified_people
    }), 200

# -----------------------------
# 13) Chatbot Interaction Endpoint
# -----------------------------
@app.route("/process_prompt", methods=["POST"])
def process_prompt():
    data = request.json
    user_prompt = data.get("prompt","").strip()
    if not user_prompt:
        return jsonify({"error":"No prompt provided"}), 400

    # Add user message
    conversation_memory.append({"role":"user","content":user_prompt})

    # Build conversation string
    conv_str = ""
    for msg in conversation_memory:
        if msg["role"] == "system":
            conv_str += f"System: {msg['content']}\n"
        elif msg["role"] == "user":
            conv_str += f"User: {msg['content']}\n"
        else:
            conv_str += f"Assistant: {msg['content']}\n"

    # Call Gemini
    try:
        response = model.generate_content(conv_str)
    except Exception as e:
        assistant_reply = f"Error generating response: {str(e)}"
    else:
        if not response.candidates:
            assistant_reply = "Hmm, I'm having trouble responding right now."
        else:
            parts = response.candidates[0].content.parts
            assistant_reply = "".join(part.text for part in parts).strip()

    # Add assistant reply
    conversation_memory.append({"role":"assistant","content":assistant_reply})

    if len(conversation_memory) > MAX_MEMORY:
        conversation_memory.pop(0)

    return jsonify({"message": assistant_reply})

# -----------------------------
# 14) Notification Endpoint for Gemini
# -----------------------------
@app.route("/notify_gemini", methods=["POST"])
def notify_gemini():
    data = request.json
    action = data.get("action")
    details = data.get("details", "")
    if not action:
        return jsonify({"error": "No action specified"}), 400

    # Construct a message based on action
    if action == "recognize":
        message = f"Recognition Process Completed: {details}"
    elif action == "error":
        message = f"An error occurred: {details}"
    elif action == "register":
        message = f"Registered new student: {details}"
    elif action == "add_subject":
        message = f"Added new subject: {details}"
    elif action == "update_attendance":
        message = f"Attendance updated: {details}"
    elif action == "download_excel":
        message = f"Downloaded attendance records as Excel."
    elif action == "download_template":
        message = f"Downloaded attendance template."
    elif action == "upload_excel":
        message = f"Uploaded attendance records from Excel."
    else:
        message = f"Action performed: {action}. Details: {details}"

    # Add assistant message to conversation
    conversation_memory.append({"role":"assistant","content":message})
    if len(conversation_memory) > MAX_MEMORY:
        conversation_memory.pop(0)
    log_event("Gemini Notification", f"Action: {action}, Details: {details}")

    return jsonify({"message": "Notification sent to Gemini."}), 200

# -----------------------------
# 15) Run App
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=True)
