import os
import sys
import base64
import json
import io
from datetime import datetime
import logging

import cv2
import numpy as np
from PIL import Image, ImageEnhance
from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin

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

base64_cred_str = os.environ.get("FIREBASE_ADMIN_CREDENTIALS_BASE64")
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
# 4) Flask App Setup
# -----------------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_default_secret_key")  # Change this in production

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# -----------------------------
# 5) User Model
# -----------------------------
class User(UserMixin):
    def __init__(self, user_id, username, role, classes=None):
        self.id = user_id
        self.username = username
        self.role = role
        self.classes = classes or []

# -----------------------------
# 6) User Loader
# -----------------------------
@login_manager.user_loader
def load_user(user_id):
    user_doc = db.collection("users").document(user_id).get()
    if user_doc.exists:
        user_data = user_doc.to_dict()
        return User(
            user_id=user_doc.id,
            username=user_data.get("username"),
            role=user_data.get("role"),
            classes=user_data.get("classes", [])
        )
    return None

# -----------------------------
# 7) Routes
# -----------------------------

@app.route("/")
@login_required
def index():
    return render_template("index.html")

# -----------------------------
# 7.1) Login Route
# -----------------------------
from werkzeug.security import generate_password_hash, check_password_hash

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Query Firestore for the user
        users_ref = db.collection("users")
        query = users_ref.where("username", "==", username).stream()
        
        user_doc = None
        for doc in query:
            user_doc = doc
            break
        
        if user_doc:
            user_data = user_doc.to_dict()
            if check_password_hash(user_data.get("password"), password):
                user = User(
                    user_id=user_doc.id,
                    username=user_data.get("username"),
                    role=user_data.get("role"),
                    classes=user_data.get("classes", [])
                )
                login_user(user)
                flash("Logged in successfully.", "success")
                return redirect(url_for("index"))
            else:
                flash("Invalid username or password.", "danger")
        else:
            flash("Invalid username or password.", "danger")
    
    return render_template("login.html")

# -----------------------------
# 7.2) Logout Route
# -----------------------------
@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# -----------------------------
# 7.3) Create User Route (Admin Only)
# -----------------------------
@app.route("/admin/create_user", methods=["GET", "POST"])
@login_required
def create_user():
    if current_user.role != "admin":
        flash("Access denied.", "danger")
        return redirect(url_for("index"))
    
    # Fetch existing classes for assignment (assuming a 'classes' collection exists)
    classes_ref = db.collection("classes").stream()
    classes = [doc.id for doc in classes_ref]
    
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")
        classes_selected = request.form.getlist("classes")
        
        if not username or not password or not role:
            flash("Please fill out all required fields.", "warning")
            return render_template("create_user.html", classes=classes)
        
        # Check if username already exists
        existing_user = db.collection("users").where("username", "==", username).stream()
        if any(True for _ in existing_user):
            flash("Username already exists.", "warning")
            return render_template("create_user.html", classes=classes)
        
        # Hash the password
        hashed_password = generate_password_hash(password, method='sha256')
        
        # Prepare user data
        user_data = {
            "username": username,
            "password": hashed_password,
            "role": role
        }
        
        if role == "teacher":
            user_data["classes"] = classes_selected
        
        # Add user to Firestore
        db.collection("users").add(user_data)
        flash("User created successfully.", "success")
        return redirect(url_for("index"))
    
    return render_template("create_user.html", classes=classes)

# -----------------------------
# 7.4) Registration Route
# -----------------------------
@app.route("/register", methods=["GET", "POST"])
@login_required
def register():
    if current_user.role not in ['admin', 'teacher']:
        flash("Access denied.", "danger")
        return redirect(url_for("index"))
    
    if request.method == "POST":
        name = request.json.get("name")
        student_id = request.json.get("student_id")
        image_data = request.json.get("image")
        
        if not name or not student_id or not image_data:
            return jsonify({"error": "Missing data"}), 400
        
        # Decode image
        try:
            header, encoded = image_data.split(",", 1)
            image_bytes = base64.b64decode(encoded)
            image = Image.open(io.BytesIO(image_bytes))
            buffered = io.BytesIO()
            image = image.convert("RGB")
            image.save(buffered, format="JPEG")
            byte_image = buffered.getvalue()
        except Exception as e:
            return jsonify({"error": f"Invalid image data: {str(e)}"}), 400
        
        # Enhance image if needed
        # (Optional) Use OpenCV or Pillow to enhance the image
        
        # Index face in Rekognition
        try:
            response = rekognition_client.index_faces(
                CollectionId=COLLECTION_ID,
                Image={'Bytes': byte_image},
                ExternalImageId=student_id,  # Using student_id as ExternalImageId
                DetectionAttributes=['DEFAULT']
            )
            if not response['FaceRecords']:
                return jsonify({"error": "No face detected in the image."}), 400
            face_id = response['FaceRecords'][0]['Face']['FaceId']
        except Exception as e:
            return jsonify({"error": f"Error indexing face: {str(e)}"}), 500
        
        # Store student data in Firestore
        try:
            student_data = {
                "student_id": student_id,
                "name": name,
                "face_id": face_id,
                "registered_by": current_user.username,
                "registered_at": datetime.utcnow().isoformat()
            }
            db.collection("students").document(student_id).set(student_data)
        except Exception as e:
            return jsonify({"error": f"Error saving student data: {str(e)}"}), 500
        
        return jsonify({"message": "Student registered successfully."}), 200
    
    return jsonify({"error": "Invalid request method."}), 405

# -----------------------------
# 7.5) Recognize Route
# -----------------------------
@app.route("/recognize", methods=["GET", "POST"])
@login_required
def recognize():
    if current_user.role not in ['admin', 'teacher', 'student']:
        return jsonify({"error": "Unauthorized access."}), 403
    
    if request.method == "POST":
        image_data = request.json.get("image")
        subject_id = request.json.get("subject_id")  # Optional
        
        if not image_data:
            return jsonify({"error": "No image provided."}), 400
        
        # Decode image
        try:
            header, encoded = image_data.split(",", 1)
            image_bytes = base64.b64decode(encoded)
            image = Image.open(io.BytesIO(image_bytes))
            buffered = io.BytesIO()
            image = image.convert("RGB")
            image.save(buffered, format="JPEG")
            byte_image = buffered.getvalue()
        except Exception as e:
            return jsonify({"error": f"Invalid image data: {str(e)}"}), 400
        
        # Recognize faces using Rekognition
        try:
            response = rekognition_client.search_faces_by_image(
                CollectionId=COLLECTION_ID,
                Image={'Bytes': byte_image},
                FaceMatchThreshold=80,
                MaxFaces=10
            )
            face_matches = response.get('FaceMatches', [])
            total_faces = len(face_matches)
            identified_people = []
            
            for match in face_matches:
                face = match['Face']
                student_id = face['ExternalImageId']
                confidence = face['Confidence']
                
                # Fetch student details from Firestore
                student_doc = db.collection("students").document(student_id).get()
                if student_doc.exists:
                    student_data = student_doc.to_dict()
                    identified_people.append({
                        "face_number": len(identified_people) + 1,
                        "name": student_data.get("name"),
                        "student_id": student_id,
                        "confidence": round(confidence, 2)
                    })
                    
                    # Log attendance
                    attendance_data = {
                        "student_id": student_id,
                        "name": student_data.get("name"),
                        "timestamp": datetime.utcnow().isoformat(),
                        "subject_id": subject_id or "",
                        "subject_name": "",  # Fetch subject name based on subject_id if provided
                        "status": "PRESENT",
                        "recorded_by": current_user.username
                    }
                    db.collection("attendance").add(attendance_data)
            return jsonify({
                "message": f"Recognized {total_faces} face(s).",
                "total_faces": total_faces,
                "identified_people": identified_people
            }), 200
        except Exception as e:
            return jsonify({"error": f"Error recognizing faces: {str(e)}"}), 500
    
    return jsonify({"error": "Invalid request method."}), 405

# -----------------------------
# 7.6) Subjects Management Routes
# -----------------------------

@app.route("/subjects", methods=["GET", "POST"])
@login_required
def manage_subjects():
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({"error": "Unauthorized access."}), 403
    
    if request.method == "POST":
        action = request.json.get("action")
        subject_id = request.json.get("subject_id")
        subject_name = request.json.get("subject_name")
        
        if action == "add":
            if not subject_name:
                return jsonify({"error": "Subject name is required."}), 400
            try:
                new_subject = {
                    "name": subject_name,
                    "created_at": datetime.utcnow().isoformat()
                }
                db.collection("subjects").add(new_subject)
                return jsonify({"message": "Subject added successfully."}), 200
            except Exception as e:
                return jsonify({"error": f"Error adding subject: {str(e)}"}), 500
        
        elif action == "edit":
            if not subject_id or not subject_name:
                return jsonify({"error": "Subject ID and name are required."}), 400
            try:
                subject_ref = db.collection("subjects").document(subject_id)
                subject_ref.update({"name": subject_name, "updated_at": datetime.utcnow().isoformat()})
                return jsonify({"message": "Subject updated successfully."}), 200
            except Exception as e:
                return jsonify({"error": f"Error updating subject: {str(e)}"}), 500
        
        elif action == "delete":
            if not subject_id:
                return jsonify({"error": "Subject ID is required."}), 400
            try:
                db.collection("subjects").document(subject_id).delete()
                return jsonify({"message": "Subject deleted successfully."}), 200
            except Exception as e:
                return jsonify({"error": f"Error deleting subject: {str(e)}"}), 500
        else:
            return jsonify({"error": "Invalid action."}), 400
    
    # GET request to fetch all subjects
    try:
        subjects = db.collection("subjects").stream()
        subjects_list = [{"id": subj.id, "name": subj.to_dict().get("name")} for subj in subjects]
        return jsonify({"subjects": subjects_list}), 200
    except Exception as e:
        return jsonify({"error": f"Error fetching subjects: {str(e)}"}), 500

# -----------------------------
# 7.7) Attendance Management Routes
# -----------------------------
import openpyxl
from io import BytesIO

@app.route("/api/attendance/download_template", methods=["GET"])
@login_required
def download_attendance_template():
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({"error": "Unauthorized access."}), 403
    
    wb = openpyxl.Workbook()
    ws = wb.active
    headers = ["doc_id","student_id","name","subject_id","subject_name","timestamp","status","recorded_by"]
    ws.append(headers)
    
    # Save the workbook to a bytes buffer
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="attendance_template.xlsx"
    )

@app.route("/api/attendance/upload", methods=["POST"])
@login_required
def upload_attendance_excel():
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({"error": "Unauthorized access."}), 403
    
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if not file.filename.endswith(".xlsx"):
        return jsonify({"error": "Please upload a .xlsx file"}), 400

    try:
        wb = openpyxl.load_workbook(file)
    except Exception as e:
        return jsonify({"error": f"Failed to read Excel file: {str(e)}"}), 400

    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    expected = ("doc_id","student_id","name","subject_id","subject_name","timestamp","status","recorded_by")
    if not rows or rows[0] != expected:
        return jsonify({"error": "Incorrect template format"}), 400

    for row in rows[1:]:
        doc_id, student_id, name, subject_id, subject_name, timestamp, status, recorded_by = row
        if doc_id:
            doc_data = {
                "student_id": student_id or "",
                "name": name or "",
                "subject_id": subject_id or "",
                "subject_name": subject_name or "",
                "timestamp": timestamp or "",
                "status": status or "",
                "recorded_by": recorded_by or current_user.username
            }
            db.collection("attendance").document(doc_id).set(doc_data, merge=True)
        else:
            new_doc = {
                "student_id": student_id or "",
                "name": name or "",
                "subject_id": subject_id or "",
                "subject_name": subject_name or "",
                "timestamp": timestamp or "",
                "status": status or "",
                "recorded_by": current_user.username
            }
            db.collection("attendance").add(new_doc)

    return jsonify({"message": "Excel data imported successfully."})

# -----------------------------
# 7.8) Gemini Chat Endpoint
# -----------------------------
@app.route("/process_prompt", methods=["POST"])
@login_required
def process_prompt():
    if current_user.role != "admin":
        return jsonify({"error": "Only admin can use this feature."}), 403

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

    # Process Gemini command if any
    if assistant_reply.startswith("EXECUTE:"):
        command = assistant_reply[len("EXECUTE:"):].strip()
        execution_result = execute_admin_command(command)
        assistant_reply += f"\nCommand Execution Result: {execution_result}"

    # Add assistant reply
    conversation_memory.append({"role":"assistant","content":assistant_reply})

    if len(conversation_memory) > MAX_MEMORY:
        conversation_memory.pop(0)

    return jsonify({"message": assistant_reply})

def execute_admin_command(command):
    """
    Parses and executes admin commands.
    Implement command parsing and execution logic here.
    """
    # Example: Create a new subject
    if command.startswith("CREATE SUBJECT"):
        try:
            subject_name = command[len("CREATE SUBJECT"):].strip()
            if not subject_name:
                return "No subject name provided."
            doc_ref = db.collection("subjects").document()
            doc_ref.set({
                "name": subject_name,
                "created_at": datetime.utcnow().isoformat()
            })
            return f"Subject '{subject_name}' created successfully."
        except Exception as e:
            return f"Failed to create subject: {str(e)}"
    elif command.startswith("DELETE SUBJECT"):
        try:
            subject_name = command[len("DELETE SUBJECT"):].strip()
            if not subject_name:
                return "No subject name provided."
            subjects = db.collection("subjects").where("name", "==", subject_name).stream()
            deleted = False
            for subj in subjects:
                subj.reference.delete()
                deleted = True
            if deleted:
                return f"Subject '{subject_name}' deleted successfully."
            else:
                return f"Subject '{subject_name}' not found."
        except Exception as e:
            return f"Failed to delete subject: {str(e)}"
    else:
        return "Unknown command."

# -----------------------------
# 8) Gemini Chatbot Frontend Integration
# -----------------------------

# Note: Ensure that your `static/script.js` handles sending prompts to `/process_prompt`
# and displaying responses in the chatbot window.

# -----------------------------
# 9) Additional Routes (Subjects, Attendance, etc.)
# -----------------------------
# These routes were covered in previous sections (7.4, 7.6). Ensure all are correctly implemented.

# -----------------------------
# 10) Run App
# -----------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

from werkzeug.security import generate_password_hash

@app.route('/create_initial_admin', methods=['GET'])
def create_initial_admin():
    # Check if any admin exists
    admins = db.collection('users').where('role', '==', 'admin').stream()
    admin_exists = False
    for admin in admins:
        admin_exists = True
        break

    if admin_exists:
        return "Admin already exists. Cannot create another initial admin.", 400

    # Define initial admin credentials
    initial_admin_username = 'admin'  # Change as needed
    initial_admin_password = 'AdminPassword123'  # Change as needed

    # Hash the password
    hashed_password = generate_password_hash(initial_admin_password, method='sha256')

    # Create admin user document
    admin_data = {
        'username': initial_admin_username,
        'password': hashed_password,
        'role': 'admin',
        'classes': []  # Not necessary for admin
    }

    db.collection('users').add(admin_data)

    return f"Initial admin '{initial_admin_username}' created successfully.", 200