import os
import sys
import base64
import json
import io
from datetime import datetime
import logging
import re

import cv2
import numpy as np
from PIL import Image, ImageEnhance
from flask import Flask, request, jsonify, render_template, send_file
from flask_socketio import SocketIO, emit

# -----------------------------
# 1) AWS Rekognition Setup
# -----------------------------
import boto3

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
        print(f"Collection '{collection_id}' created.")
    except rekognition_client.exceptions.ResourceAlreadyExistsException:
        print(f"Collection '{collection_id}' already exists.")

create_collection_if_not_exists(COLLECTION_ID)

# -----------------------------
# 2) Firebase Firestore Setup
# -----------------------------
import firebase_admin
from firebase_admin import credentials, firestore

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
import google.generativeai as genai

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
"""

# Start the conversation with a system message
conversation_memory.append({"role": "system", "content": system_context})

# -----------------------------
# 4) Flask App
# -----------------------------
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # Initialize SocketIO

# -----------------------------
# 5) Image Enhancement Function (Using OpenCV and Pillow)
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
# 6) Routes
# -----------------------------

# Root route to serve the frontend
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# Register Face (GET/POST)
@app.route("/register", methods=["GET","POST"])
def register_face():
    if request.method == "GET":
        return "Welcome to /register. Please POST with {name, student_id, image} to register."

    data = request.json
    name = data.get('name')
    student_id = data.get('student_id')
    image = data.get('image')
    if not name or not student_id or not image:
        error_message = "Missing name, student_id, or image."
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"message": error_message}), 400

    sanitized_name = "".join(c if c.isalnum() or c in "_-." else "_" for c in name)
    image_data = image.split(",")[1]
    image_bytes = base64.b64decode(image_data)

    # Enhance image before indexing
    pil_image = Image.open(io.BytesIO(image_bytes))
    enhanced_image = enhance_image(pil_image)
    buffered = io.BytesIO()
    enhanced_image.save(buffered, format="JPEG")
    enhanced_image_bytes = buffered.getvalue()

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
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"message": error_message}), 500

    if not response.get('FaceRecords'):
        error_message = "No face detected in the image."
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"message": error_message}), 400

    success_message = f"Student {name} with ID {student_id} registered successfully!"
    socketio.emit('action_feedback', {'message': success_message, 'type': 'success'})
    return jsonify({"message": success_message}), 200

# Recognize Face (GET/POST)
@app.route("/recognize", methods=["GET","POST"])
def recognize_face():
    if request.method == "GET":
        return "Welcome to /recognize. Please POST with {image, subject_id(optional)} to detect faces."

    data = request.json
    image_str = data.get('image')
    subject_id = data.get('subject_id') or ""
    if not image_str:
        error_message = "No image provided."
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"message": error_message}), 400

    # Optionally fetch subject name
    subject_name = ""
    if subject_id:
        sdoc = db.collection("subjects").document(subject_id).get()
        if sdoc.exists:
            subject_name = sdoc.to_dict().get("name", "")
        else:
            subject_name = "Unknown Subject"

    image_data = image_str.split(",")[1]
    image_bytes = base64.b64decode(image_data)

    # Enhance image before detection
    pil_image = Image.open(io.BytesIO(image_bytes))
    enhanced_image = enhance_image(pil_image)
    buffered = io.BytesIO()
    enhanced_image.save(buffered, format="JPEG")
    enhanced_image_bytes = buffered.getvalue()

    try:
        # Detect faces in the image
        detect_response = rekognition_client.detect_faces(
            Image={'Bytes': enhanced_image_bytes},
            Attributes=['ALL']
        )
    except Exception as e:
        error_message = f"Failed to detect faces: {str(e)}"
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"message": error_message}), 500

    faces = detect_response.get('FaceDetails', [])
    face_count = len(faces)
    identified_people = []

    if face_count == 0:
        message = "No faces detected in the image."
        socketio.emit('action_feedback', {'message': message, 'type': 'info'})
        return jsonify({
            "message": message,
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
                "face_number": idx+1,
                "message": f"Error searching face {idx+1}: {str(e)}",
                "confidence": "N/A"
            })
            socketio.emit('action_feedback', {'message': f"Error searching face {idx+1}: {str(e)}", 'type': 'error'})
            continue

        matches = search_response.get('FaceMatches', [])
        if not matches:
            identified_people.append({
                "face_number": idx+1,
                "message": "Face not recognized",
                "confidence": "N/A"
            })
            socketio.emit('action_feedback', {'message': f"Face {idx+1} not recognized.", 'type': 'info'})
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
            "face_number": idx+1,
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
                socketio.emit('action_feedback', {'message': f"Attendance logged for {rec_name} (ID: {rec_id}).", 'type': 'success'})
            except Exception as e:
                error_message = f"Failed to log attendance for {rec_name} (ID: {rec_id}): {str(e)}"
                identified_people[-1]["message"] = error_message
                socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})

    return jsonify({
        "message": f"{face_count} face(s) detected in the photo.",
        "total_faces": face_count,
        "identified_people": identified_people
    }), 200

# SUBJECTS
@app.route("/add_subject", methods=["POST"])
def add_subject():
    data = request.json
    subject_name = data.get("subject_name")
    if not subject_name:
        error_message = "No subject_name provided."
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"error": error_message}), 400
    try:
        doc_ref = db.collection("subjects").document()
        doc_ref.set({
            "name": subject_name.strip(),
            "created_at": datetime.utcnow().isoformat()
        })
        success_message = f"Subject '{subject_name}' added successfully!"
        socketio.emit('action_feedback', {'message': success_message, 'type': 'success'})
        return jsonify({"message": success_message}), 200
    except Exception as e:
        error_message = f"Failed to add subject '{subject_name}': {str(e)}"
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"error": error_message}), 500

@app.route("/get_subjects", methods=["GET"])
def get_subjects():
    try:
        subs = db.collection("subjects").stream()
        subj_list = []
        for s in subs:
            d = s.to_dict()
            subj_list.append({"id": s.id, "name": d.get("name","")})
        return jsonify({"subjects": subj_list}), 200
    except Exception as e:
        error_message = f"Failed to retrieve subjects: {str(e)}"
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"error": error_message}), 500

# ATTENDANCE
import openpyxl
from openpyxl import Workbook

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
            error_message = "Invalid start_date format. Use YYYY-MM-DD."
            socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
            return jsonify({"error": error_message}), 400
    if end_date:
        try:
            dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            query = query.where("timestamp", "<=", dt_end.isoformat())
        except ValueError:
            error_message = "Invalid end_date format. Use YYYY-MM-DD."
            socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
            return jsonify({"error": error_message}), 400

    try:
        results = query.stream()
        out_list = []
        for doc_ in results:
            dd = doc_.to_dict()
            dd["doc_id"] = doc_.id
            out_list.append(dd)
        return jsonify(out_list)
    except Exception as e:
        error_message = f"Failed to retrieve attendance records: {str(e)}"
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"error": error_message}), 500

@app.route("/api/attendance/update", methods=["POST"])
def update_attendance():
    data = request.json
    records = data.get("records", [])
    if not records:
        error_message = "No records provided for update."
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"error": error_message}), 400

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
        success_message = "Attendance records updated successfully."
        socketio.emit('action_feedback', {'message': success_message, 'type': 'success'})
        return jsonify({"message": success_message}), 200
    except Exception as e:
        error_message = f"Failed to update attendance records: {str(e)}"
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"error": error_message}), 500

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
            error_message = "Invalid start_date format. Use YYYY-MM-DD."
            socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
            return jsonify({"error": error_message}), 400
    if end_date:
        try:
            dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
            query = query.where("timestamp", "<=", dt_end.isoformat())
        except ValueError:
            error_message = "Invalid end_date format. Use YYYY-MM-DD."
            socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
            return jsonify({"error": error_message}), 400

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
        socketio.emit('action_feedback', {'message': "Attendance data downloaded.", 'type': 'success'})
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="attendance.xlsx"
        )
    except Exception as e:
        error_message = f"Failed to download attendance Excel: {str(e)}"
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"error": error_message}), 500

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
        socketio.emit('action_feedback', {'message': "Attendance template downloaded.", 'type': 'success'})
        return send_file(
            output,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="attendance_template.xlsx"
        )
    except Exception as e:
        error_message = f"Failed to download template: {str(e)}"
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"error": error_message}), 500

@app.route("/api/attendance/upload", methods=["POST"])
def upload_attendance_excel():
    if "file" not in request.files:
        error_message = "No file uploaded."
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"error": error_message}), 400
    file = request.files["file"]
    if not file.filename.endswith(".xlsx"):
        error_message = "Please upload a .xlsx file."
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"error": error_message}), 400

    try:
        wb = openpyxl.load_workbook(file)
    except Exception as e:
        error_message = f"Failed to read Excel file: {str(e)}"
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"error": error_message}), 400

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    expected = ("doc_id","student_id","name","subject_id","subject_name","timestamp","status")
    if not rows or rows[0] != expected:
        error_message = "Incorrect template format."
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"error": error_message}), 400

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
        success_message = "Excel data imported successfully."
        socketio.emit('action_feedback', {'message': success_message, 'type': 'success'})
        return jsonify({"message": success_message}), 200
    except Exception as e:
        error_message = f"Failed to upload Excel data: {str(e)}"
        socketio.emit('action_feedback', {'message': error_message, 'type': 'error'})
        return jsonify({"error": error_message}), 500

# -----------------------------
# 7) Gemini Chat Endpoint
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

    # Check if the assistant reply contains actionable commands
    # (Implement command parsing and handling if needed)

    return jsonify({"message": assistant_reply})

# -----------------------------
# 8) Run App
# -----------------------------
if __name__ == "__main__":
    # Note: The following run block is only for local development.
    # In production, Render will use Gunicorn to run the app.
    socketio.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True, allow_unsafe_werkzeug=True)
