import os
import sys
import base64
import json
import io
from datetime import datetime
import logging
import uuid
from werkzeug.utils import secure_filename

import cv2
import numpy as np
from PIL import Image, ImageEnhance
from flask import (
    Flask,
    request,
    jsonify,
    render_template_string,
    send_file,
    redirect,
    url_for,
    flash,
    session
)
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
    UserMixin,
)
from werkzeug.security import generate_password_hash, check_password_hash
from argon2 import PasswordHasher

# Initialize the Password Hasher
ph = PasswordHasher()

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
# 4) Flask App Initialization
# -----------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_default_secret_key")

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to 'login' when login is required

# -----------------------------
# 5) User Model and Authentication
# -----------------------------

class User(UserMixin):
    def __init__(self, id, username, password_hash, role, classes=None):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role  # 'admin', 'teacher', 'student'
        self.classes = classes or []  # List of class IDs (for teachers)

# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    user_doc = db.collection("users").document(user_id).get()
    if user_doc.exists:
        user_data = user_doc.to_dict()
        return User(
            id=user_doc.id,
            username=user_data.get("username"),
            password_hash=user_data.get("password_hash"),
            role=user_data.get("role"),
            classes=user_data.get("classes", [])
        )
    return None

# -----------------------------
# 6) Login and Registration Routes
# -----------------------------

# HTML template for login page
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Login - Facial Recognition Attendance</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <!-- Bootstrap CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
  <style>
    body { display: flex; align-items: center; justify-content: center; height: 100vh; background-color: #f8f9fa; }
    .login-container { background-color: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
  </style>
</head>
<body>
  <div class="login-container">
    <h3 class="mb-4">Login</h3>
    <form method="POST" action="{{ url_for('login') }}">
      <div class="mb-3">
        <label for="username" class="form-label">Username</label>
        <input type="text" class="form-control" id="username" name="username" required />
      </div>
      <div class="mb-3">
        <label for="password" class="form-label">Password</label>
        <input type="password" class="form-control" id="password" name="password" required />
      </div>
      <button type="submit" class="btn btn-primary">Login</button>
    </form>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <div class="mt-3">
          {% for category, message in messages %}
            <div class="alert alert-{{ category }}" role="alert">
              {{ message }}
            </div>
          {% endfor %}
        </div>
      {% endif %}
    {% endwith %}
  </div>
</body>
</html>
"""

#define role_required decorator
from functools import wraps

def role_required(required_roles):
    def decorator(f):
        @wraps(f)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in required_roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return wrapped
    return decorator

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()

        # Fetch user from Firestore
        users_ref = db.collection("users").where("username", "==", username).stream()
        user_doc = next(users_ref, None)

        if user_doc:
            user_data = user_doc.to_dict()
            try:
                ph.verify(user_data['password_hash'], password)
                # If verification is successful, proceed to log the user in
                user = User(
                    username=user_data['username'],
                    role=user_data['role'],
                    classes=user_data.get('classes', [])
                )
                login_user(user)
                flash("Logged in successfully.", "success")
                return redirect(url_for('dashboard'))
            except:
                flash("Invalid password.", "danger")
        else:
            flash("User not found.", "danger")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# -----------------------------
# 7) Admin Routes for User Management
# -----------------------------

# HTML template for admin panel
ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Admin Panel - User Management</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <!-- Bootstrap CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet" />
</head>
<body class="container mt-4">
  <h2>Admin Panel - User Management</h2>
  
  <!-- Create User Form -->
  <div class="card mt-3">
    <div class="card-header">
      Create New User
    </div>
    <div class="card-body">
      <form method="POST" action="{{ url_for('create_user') }}">
        <div class="mb-3">
          <label for="username" class="form-label">Username</label>
          <input type="text" class="form-control" id="username" name="username" required />
        </div>
        <div class="mb-3">
          <label for="password" class="form-label">Password</label>
          <input type="password" class="form-control" id="password" name="password" required />
        </div>
        <div class="mb-3">
          <label for="role" class="form-label">Role</label>
          <select class="form-select" id="role" name="role" required>
            <option value="">Select Role</option>
            <option value="teacher">Teacher</option>
            <option value="student">Student</option>
          </select>
        </div>
        <div class="mb-3" id="classes_div" style="display: none;">
          <label for="classes" class="form-label">Assign Classes (Comma-Separated IDs)</label>
          <input type="text" class="form-control" id="classes" name="classes" placeholder="e.g., math101,phy201" />
        </div>
        <button type="submit" class="btn btn-primary">Create User</button>
      </form>
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          <div class="mt-3">
            {% for category, message in messages %}
              <div class="alert alert-{{ category }}" role="alert">
                {{ message }}
              </div>
            {% endfor %}
          </div>
        {% endif %}
      {% endwith %}
    </div>
  </div>
  
  <!-- Existing Users List -->
  <div class="card mt-4">
    <div class="card-header">
      Existing Users
    </div>
    <div class="card-body">
      <table class="table table-bordered">
        <thead>
          <tr>
            <th>Username</th>
            <th>Role</th>
            <th>Assigned Classes</th>
          </tr>
        </thead>
        <tbody>
          {% for user in users %}
            <tr>
              <td>{{ user.username }}</td>
              <td>{{ user.role.capitalize() }}</td>
              <td>
                {% if user.classes %}
                  {{ ", ".join(user.classes) }}
                {% else %}
                  N/A
                {% endif %}
              </td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
  
  <a href="{{ url_for('index') }}" class="btn btn-secondary mt-3">Back to Dashboard</a>

  <!-- Bootstrap JS -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    document.getElementById('role').addEventListener('change', function() {
      if (this.value === 'teacher') {
        document.getElementById('classes_div').style.display = 'block';
      } else {
        document.getElementById('classes_div').style.display = 'none';
      }
    });
  </script>
</body>
</html>
"""

@app.route("/admin", methods=["GET"])
@role_required(['admin'])
def admin_panel():
    # Fetch all users except admin
    users_ref = db.collection("users")
    users = users_ref.stream()
    users_list = []
    for user_doc in users:
        user_data = user_doc.to_dict()
        if user_data.get("role") == "admin":
            continue  # Skip admin accounts
        users_list.append({
            "username": user_data.get("username"),
            "role": user_data.get("role"),
            "classes": user_data.get("classes", [])
        })
    return render_template_string(ADMIN_HTML, users=users_list)

@app.route("/admin/create_user", methods=["GET", "POST"])
@login_required
@role_required(['admin'])
def create_user_route():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password").strip()
        role = request.form.get("role").strip().lower()
        classes_input = request.form.get("classes").strip()  # Comma-separated for teachers
        photo = request.files.get("photo")

        if not username or not password or role not in ['student', 'teacher']:
            flash("Invalid input. Ensure username, password, and valid role are provided.", "danger")
            return redirect(url_for('create_user_route'))

        # Check if user already exists
        users_ref = db.collection("users").where("username", "==", username).stream()
        if any(True for _ in users_ref):
            flash("Username already exists. Choose a different username.", "danger")
            return redirect(url_for('create_user_route'))

        # Handle photo upload for students
        photo_filename = ""
        if role == 'student':
            if not photo or photo.filename == '':
                flash("Student photo is required.", "danger")
                return redirect(url_for('create_user_route'))
            if photo and allowed_file(photo.filename):
                filename = secure_filename(photo.filename)
                unique_filename = f"{username}_{uuid.uuid4().hex[:8]}_{filename}"
                photo.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                photo_filename = unique_filename
            else:
                flash("Invalid photo format. Allowed formats: png, jpg, jpeg.", "danger")
                return redirect(url_for('create_user_route'))

        # Assign unique ID based on role
        unique_id = generate_unique_id('S') if role == 'student' else generate_unique_id('T')
        username = unique_id  # Overriding username with unique ID

        # Process classes
        classes = []
        if role == 'teacher':
            classes = [cls.strip() for cls in classes_input.split(",") if cls.strip()]
            if not classes:
                flash("Teachers must be assigned to at least one class.", "danger")
                return redirect(url_for('create_user_route'))
        elif role == 'student':
            # Auto assign class based on some logic, e.g., student ID
            class_id = assign_class_to_student(username)
            classes = [class_id]

        # Hash the password
        ph = PasswordHasher()
        password_hash = ph.hash(password)

        # Create user data
        user_data = {
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "classes": classes
        }
        if role == 'student':
            user_data["photo"] = photo_filename

        # Add user to Firestore
        db.collection("users").add(user_data)
        flash(f"{role.capitalize()} user '{username}' created successfully.", "success")
        return redirect(url_for('dashboard'))

    return render_template("create_user.html")

# -----------------------------
# 8) Single-Page HTML + Chat Widget with Role-Based Tabs
# -----------------------------
INDEX_HTML = """
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
  <style>
    body { margin: 20px; }
    .nav-tabs .nav-link { color: #555; }
    .nav-tabs .nav-link.active { color: #000; font-weight: bold; }
    #attendanceTable td[contenteditable="true"] { background-color: #fcf8e3; }

    /* Chatbot Toggle Button */
    #chatbotToggle {
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 999;
      background-color: #0d6efd;
      color: #fff;
      border: none;
      border-radius: 50%;
      width: 50px;
      height: 50px;
      font-size: 22px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    #chatbotToggle:hover { background-color: #0b5ed7; }

    /* Chat Window */
    #chatbotWindow {
      position: fixed;
      bottom: 80px;
      right: 20px;
      width: 300px;
      max-height: 400px;
      border: 1px solid #ccc;
      border-radius: 10px;
      background-color: #fff;
      box-shadow: 0 0 10px rgba(0,0,0,0.2);
      display: none;
      flex-direction: column;
      z-index: 1000;
    }
    #chatHeader {
      background-color: #0d6efd;
      color: #fff;
      padding: 10px;
      border-radius: 10px 10px 0 0;
      font-weight: bold;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    #chatHeader .close-btn {
      background: none;
      border: none;
      color: #fff;
      font-weight: bold;
      cursor: pointer;
      font-size: 16px;
    }
    #chatMessages {
      flex: 1;
      overflow-y: auto;
      padding: 10px;
      font-size: 14px;
    }
    .message { margin-bottom: 10px; }
    .message.user { text-align: right; }
    .message.assistant { text-align: left; color: #333; }
    #chatInputArea {
      display: flex; border-top: 1px solid #ddd;
    }
    #chatInput {
      flex: 1; padding: 8px; border: none; outline: none; font-size: 14px;
    }
    #chatSendBtn {
      background-color: #0d6efd; color: #fff;
      border: none; padding: 0 15px; cursor: pointer;
    }
    #chatSendBtn:hover { background-color: #0b5ed7; }
  </style>
</head>
<body class="container">

<h1 class="my-4">Facial Recognition Attendance + Gemini Chat</h1>

<!-- Nav Tabs -->
<ul class="nav nav-tabs" id="mainTabs" role="tablist">
  {% if current_user.role in ['admin', 'teacher'] %}
  <li class="nav-item">
    <button class="nav-link {% if active_tab == 'register' %}active{% endif %}" id="register-tab" data-bs-toggle="tab" data-bs-target="#register" type="button" role="tab">
      Register
    </button>
  </li>
  {% endif %}
  <li class="nav-item">
    <button class="nav-link {% if active_tab == 'recognize' %}active{% endif %}" id="recognize-tab" data-bs-toggle="tab" data-bs-target="#recognize" type="button" role="tab">
      Recognize
    </button>
  </li>
  {% if current_user.role in ['admin', 'teacher'] %}
  <li class="nav-item">
    <button class="nav-link {% if active_tab == 'subjects' %}active{% endif %}" id="subjects-tab" data-bs-toggle="tab" data-bs-target="#subjects" type="button" role="tab">
      Subjects
    </button>
  </li>
  <li class="nav-item">
    <button class="nav-link {% if active_tab == 'attendance' %}active{% endif %}" id="attendance-tab" data-bs-toggle="tab" data-bs-target="#attendance" type="button" role="tab">
      Attendance
    </button>
  </li>
  {% endif %}
  {% if current_user.role == 'admin' %}
  <li class="nav-item">
    <button class="nav-link {% if active_tab == 'admin' %}active{% endif %}" id="admin-tab" data-bs-toggle="tab" data-bs-target="#admin" type="button" role="tab">
      Admin
    </button>
  </li>
  {% endif %}
</ul>

<div class="tab-content" id="mainTabContent">
  {% if current_user.role in ['admin', 'teacher'] %}
  <!-- REGISTER -->
  <div class="tab-pane fade {% if active_tab == 'register' %}show active{% endif %} mt-4" id="register" role="tabpanel" aria-labelledby="register-tab">
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
  {% endif %}

  <!-- RECOGNIZE -->
  <div class="tab-pane fade {% if active_tab == 'recognize' %}show active{% endif %} mt-4" id="recognize" role="tabpanel" aria-labelledby="recognize-tab">
    <h3>Recognize Faces</h3>
    {% if current_user.role != 'student' %}
    <label class="form-label">Subject (optional)</label>
    <select id="rec_subject_select" class="form-control mb-2">
      <option value="">-- No Subject --</option>
    </select>
    {% endif %}
    <label class="form-label">Image</label>
    <input type="file" id="rec_image" class="form-control" accept="image/*" />
    <button onclick="recognizeFace()" class="btn btn-success mt-2">Recognize</button>
    <div id="recognize_result" class="alert alert-info mt-3" style="display:none;"></div>
  </div>

  {% if current_user.role in ['admin', 'teacher'] %}
  <!-- SUBJECTS -->
  <div class="tab-pane fade {% if active_tab == 'subjects' %}show active{% endif %} mt-4" id="subjects" role="tabpanel" aria-labelledby="subjects-tab">
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
  <div class="tab-pane fade {% if active_tab == 'attendance' %}show active{% endif %} mt-4" id="attendance" role="tabpanel" aria-labelledby="attendance-tab">
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
  {% endif %}

  {% if current_user.role == 'admin' %}
  <!-- ADMIN -->
  <div class="tab-pane fade {% if active_tab == 'admin' %}show active{% endif %} mt-4" id="admin" role="tabpanel" aria-labelledby="admin-tab">
    <h3>Admin Dashboard</h3>
    <a href="{{ url_for('admin_panel') }}" class="btn btn-primary">Manage Users</a>
    <!-- Additional Admin functionalities can be added here -->
  </div>
  {% endif %}
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

<!-- Logout Button -->
<a href="{{ url_for('logout') }}" class="btn btn-danger mt-3">Logout</a>

<!-- Scripts -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>

<script>
  /* -------------- Chatbot Code -------------- */
  const toggleBtn = document.getElementById('chatbotToggle');
  const chatWindow = document.getElementById('chatbotWindow');
  const chatCloseBtn = document.getElementById('chatCloseBtn');
  const chatMessages = document.getElementById('chatMessages');
  const chatInput = document.getElementById('chatInput');
  const chatSendBtn = document.getElementById('chatSendBtn');

  // Toggle chat window
  toggleBtn.addEventListener('click', () => {
    if (chatWindow.style.display === 'none' || chatWindow.style.display === '') {
      chatWindow.style.display = 'flex';
    } else {
      chatWindow.style.display = 'none';
    }
  });

  // Close chat window
  chatCloseBtn.addEventListener('click', () => {
    chatWindow.style.display = 'none';
  });

  function sendMessage() {
    const userMessage = chatInput.value.trim();
    if (!userMessage) return;
    addMessage(userMessage, 'user');
    chatInput.value = '';

    fetch('/process_prompt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: userMessage })
    })
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        addMessage("Error: " + data.error, 'assistant');
      } else {
        addMessage(data.message, 'assistant');
      }
    })
    .catch(err => {
      addMessage("Network or server error!", 'assistant');
      console.error(err);
    });
  }

  function addMessage(text, sender) {
    const div = document.createElement('div');
    div.classList.add('message', sender);
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  chatSendBtn.addEventListener('click', sendMessage);
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      sendMessage();
    }
  });

  /* -------------- Register + Recognize + Subjects + Attendance -------------- */
  let table;
  let attendanceData = [];

  function getBase64(file, callback) {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => callback(reader.result);
    reader.onerror = (error) => console.error('Error:', error);
  }

  /* Register Face */
  function registerFace() {
    const name = document.getElementById('reg_name').value.trim();
    const studentId = document.getElementById('reg_student_id').value.trim();
    const file = document.getElementById('reg_image').files[0];
    if (!name || !studentId || !file) {
      alert('Please provide name, student ID, and an image.');
      return;
    }
    getBase64(file, (base64Str) => {
      fetch('/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, student_id: studentId, image: base64Str })
      })
      .then(res => res.json())
      .then(data => {
        const div = document.getElementById('register_result');
        div.style.display = 'block';
        div.textContent = data.message || data.error || JSON.stringify(data);
      })
      .catch(err => console.error(err));
    });
  }

  /* Recognize Faces */
  function recognizeFace() {
    const file = document.getElementById('rec_image').files[0];
    {% if current_user.role != 'student' %}
    const subjectId = document.getElementById('rec_subject_select').value;
    {% else %}
    const subjectId = "";
    {% endif %}
    if (!file) {
      alert('Please select an image to recognize.');
      return;
    }
    getBase64(file, (base64Str) => {
      fetch('/recognize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: base64Str, subject_id: subjectId })
      })
      .then(res => res.json())
      .then(data => {
        const div = document.getElementById('recognize_result');
        div.style.display = 'block';
        let text = data.message || data.error || JSON.stringify(data);
        if (data.identified_people) {
          text += "\\n\\nIdentified People:\\n";
          data.identified_people.forEach((p) => {
            text += `- ${p.name || "Unknown"} (ID: ${p.student_id || "N/A"}), Confidence: ${p.confidence}\\n`;
          });
        }
        div.textContent = text;
      })
      .catch(err => console.error(err));
    });
  }

  /* Subjects */
  function addSubject() {
    const subjectName = document.getElementById('subject_name').value.trim();
    if (!subjectName) {
      alert('Please enter subject name.');
      return;
    }
    fetch('/add_subject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subject_name: subjectName })
    })
    .then(res => res.json())
    .then(data => {
      const div = document.getElementById('subject_result');
      div.style.display = 'block';
      div.textContent = data.message || data.error || JSON.stringify(data);
      document.getElementById('subject_name').value = '';
      loadSubjects();
    })
    .catch(err => console.error(err));
  }

  function loadSubjects() {
    fetch('/get_subjects')
    .then(res => res.json())
    .then(data => {
      const select = document.getElementById('rec_subject_select');
      select.innerHTML = '<option value="">-- No Subject --</option>';
      (data.subjects || []).forEach(sub => {
        const option = document.createElement('option');
        option.value = sub.id;
        option.textContent = sub.name;
        select.appendChild(option);
      });
      const list = document.getElementById('subjects_list');
      list.innerHTML = '';
      (data.subjects || []).forEach(sub => {
        const li = document.createElement('li');
        li.textContent = `ID: ${sub.id}, Name: ${sub.name}`;
        list.appendChild(li);
      });
    })
    .catch(err => console.error(err));
  }

  /* Attendance */
  function loadAttendance() {
    const studentId = document.getElementById('filter_student_id').value.trim();
    const subjectId = document.getElementById('filter_subject_id').value.trim();
    const startDate = document.getElementById('filter_start').value;
    const endDate = document.getElementById('filter_end').value;

    let url = '/api/attendance?';
    if (studentId) url += 'student_id=' + studentId + '&';
    if (subjectId) url += 'subject_id=' + subjectId + '&';
    if (startDate) url += 'start_date=' + startDate + '&';
    if (endDate) url += 'end_date=' + endDate + '&';

    fetch(url)
      .then(res => res.json())
      .then(data => {
        attendanceData = data;
        renderAttendanceTable(attendanceData);
      })
      .catch(err => console.error(err));
  }

  function renderAttendanceTable(data) {
    if ($.fn.DataTable.isDataTable('#attendanceTable')) {
      $('#attendanceTable').DataTable().clear().destroy();
    }
    const tbody = document.querySelector('#attendanceTable tbody');
    tbody.innerHTML = '';
    data.forEach(record => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${record.doc_id || ''}</td>
        <td contenteditable="true">${record.student_id || ''}</td>
        <td contenteditable="true">${record.name || ''}</td>
        <td contenteditable="true">${record.subject_id || ''}</td>
        <td contenteditable="true">${record.subject_name || ''}</td>
        <td contenteditable="true">${record.timestamp || ''}</td>
        <td contenteditable="true">${record.status || ''}</td>
      `;
      tbody.appendChild(row);
    });
    $('#attendanceTable').DataTable({
      paging: true,
      searching: false,
      info: false,
      responsive: true
    });
  }

  function saveEdits() {
    const rows = document.querySelectorAll('#attendanceTable tbody tr');
    const updatedRecords = [];
    rows.forEach(row => {
      const cells = row.querySelectorAll('td');
      const doc_id = cells[0].textContent.trim();
      const student_id = cells[1].textContent.trim();
      const name = cells[2].textContent.trim();
      const subject_id = cells[3].textContent.trim();
      const subject_name = cells[4].textContent.trim();
      const timestamp = cells[5].textContent.trim();
      const status = cells[6].textContent.trim();
      updatedRecords.push({ doc_id, student_id, name, subject_id, subject_name, timestamp, status });
    });
    fetch('/api/attendance/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ records: updatedRecords })
    })
    .then(res => res.json())
    .then(resp => {
      alert(resp.message || JSON.stringify(resp));
    })
    .catch(err => console.error(err));
  }

  function downloadExcel() {
    const studentId = document.getElementById('filter_student_id').value.trim();
    const subjectId = document.getElementById('filter_subject_id').value.trim();
    const startDate = document.getElementById('filter_start').value;
    const endDate = document.getElementById('filter_end').value;

    let url = '/api/attendance/download?';
    if (studentId) url += 'student_id=' + studentId + '&';
    if (subjectId) url += 'subject_id=' + subjectId + '&';
    if (startDate) url += 'start_date=' + startDate + '&';
    if (endDate) url += 'end_date=' + endDate + '&';

    window.location.href = url;
  }

  function downloadTemplate() {
    window.location.href = '/api/attendance/template';
  }

  function uploadExcel() {
    const fileInput = document.getElementById('excelFile');
    if (!fileInput.files.length) {
      alert('Please select an Excel file (.xlsx)');
      return;
    }
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    fetch('/api/attendance/upload', {
      method: 'POST',
      body: formData
    })
    .then(res => res.json())
    .then(resp => {
      alert(resp.message || resp.error || 'Excel uploaded');
      loadAttendance();
    })
    .catch(err => console.error(err));
  }

  document.addEventListener('DOMContentLoaded', () => {
    {% if current_user.role in ['admin', 'teacher'] %}
    loadSubjects();
    {% endif %}
  });
</script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
@login_required
def index():
    # Determine which tab is active based on query parameter
    active_tab = request.args.get("tab", "recognize")
    return render_template_string(INDEX_HTML, active_tab=active_tab)

# -----------------------------
# 9) Routes (Register, Recognize, Subjects, Attendance)
# -----------------------------

# Register Face (GET/POST)
@app.route("/register", methods=["GET","POST"])
@role_required(['admin', 'teacher'])
def register_face():
    if request.method == "GET":
        return "Welcome to /register. Please POST with {name, student_id, image} to register."

    data = request.json
    name = data.get('name')
    student_id = data.get('student_id')
    image = data.get('image')
    if not name or not student_id or not image:
        return jsonify({"message": "Missing name, student_id, or image"}), 400

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
        return jsonify({"message": f"Failed to index face: {str(e)}"}), 500

    if not response.get('FaceRecords'):
        return jsonify({"message": "No face detected in the image"}), 400

    return jsonify({"message": f"Student {name} with ID {student_id} registered successfully!"}), 200

# Recognize Face (GET/POST)
@app.route("/recognize", methods=["GET","POST"])
@login_required
def recognize_face():
    if request.method == "GET":
        return "Welcome to /recognize. Please POST with {image, subject_id(optional)} to detect faces."

    data = request.json
    image_str = data.get('image')
    subject_id = data.get('subject_id') or ""
    if not image_str:
        return jsonify({"message": "No image provided"}), 400

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
        return jsonify({"message": f"Failed to detect faces: {str(e)}"}), 500

    faces = detect_response.get('FaceDetails', [])
    face_count = len(faces)
    identified_people = []

    if face_count == 0:
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
            db.collection("attendance").add(doc)

    return jsonify({
        "message": f"{face_count} face(s) detected in the photo.",
        "total_faces": face_count,
        "identified_people": identified_people
    }), 200

# SUBJECTS
@app.route("/add_subject", methods=["POST"])
@login_required
@role_required(['admin'])
def add_subject():
    data = request.get_json()
    name = data.get('name', '').strip()
    details = data.get('details', '').strip()

    if not name:
        return jsonify({'status': 'danger', 'message': 'Subject name is required.'}), 400

    try:
        db.collection("subjects").add({
            "name": name,
            "details": details
        })
        return jsonify({'status': 'success', 'message': 'Subject added successfully.'})
    except Exception as e:
        return jsonify({'status': 'danger', 'message': f'Error adding subject: {str(e)}'}), 500

@app.route("/admin/update_subject/<subject_id>", methods=["POST"])
@login_required
@role_required(['admin'])
def update_subject(subject_id):
    data = request.get_json()
    name = data.get('name', '').strip()
    details = data.get('details', '').strip()

    if not name:
        return jsonify({'status': 'danger', 'message': 'Subject name is required.'}), 400

    try:
        subject_ref = db.collection("subjects").document(subject_id)
        subject_ref.update({
            "name": name,
            "details": details
        })
        return jsonify({'status': 'success', 'message': 'Subject updated successfully.'})
    except Exception as e:
        return jsonify({'status': 'danger', 'message': f'Error updating subject: {str(e)}'}), 500

@app.route("/admin/delete_subject/<subject_id>", methods=["DELETE"])
@login_required
@role_required(['admin'])
def delete_subject(subject_id):
    try:
        subject_ref = db.collection("subjects").document(subject_id)
        subject_ref.delete()
        return jsonify({'status': 'success', 'message': 'Subject deleted successfully.'})
    except Exception as e:
        return jsonify({'status': 'danger', 'message': f'Error deleting subject: {str(e)}'}), 500

# Configuration for file uploads
UPLOAD_FOLDER = '/path/to/your/static/uploads'  # Update this path accordingly
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_unique_id(prefix=''):
    """
    Generates a unique identifier with an optional prefix.
    """
    return f"{prefix}{uuid.uuid4().hex[:8]}"

def assign_class_to_student(username):
    """
    Assigns a class to a student based on their username or other criteria.
    Replace this logic with your actual class assignment process.
    """
    # Example: Assign to a default class or based on some logic
    default_class = "General101"
    return default_class

@app.route("/dashboard")
@login_required
def dashboard():
    role = current_user.role
    subjects = []
    users = []
    classes = []

    # Fetch subjects
    subjects_ref = db.collection("subjects").stream()
    for subj in subjects_ref:
        subjects.append({'id': subj.id, 'name': subj.to_dict().get('name', 'N/A')})

    # Admin functionalities
    if role == 'admin':
        users_ref = db.collection("users").stream()
        for user in users_ref:
            users.append({
                'username': user.to_dict().get('username', 'N/A'),
                'role': user.to_dict().get('role', 'N/A'),
                'classes': user.to_dict().get('classes', [])
            })

        classes_ref = db.collection("classes").stream()
        for cls in classes_ref:
            classes.append(cls.to_dict().get('class_id', 'N/A'))

    return render_template("dashboard.html", role=role, subjects=subjects, users=users, classes=classes)

def create_default_admin():
    """
    Creates a default admin user if no admin exists in the Firestore database.
    """
    try:
        # Query Firestore to check if any admin user exists
        admins = db.collection("users").where("role", "==", "admin").stream()
        admin_exists = False
        for admin in admins:
            admin_exists = True
            break

        if not admin_exists:
            # Fetch default admin credentials from environment variables
            default_admin_username = os.getenv("DEFAULT_ADMIN_USERNAME")
            default_admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD")

            if not default_admin_username or not default_admin_password:
                logger.error("Default admin credentials not set in environment variables.")
                print("Default admin credentials not set in environment variables.")
                return

            # Hash the default admin password
            password_hash = ph.hash(default_admin_password)

            # Create admin user data
            admin_data = {
                "username": default_admin_username,
                "password_hash": password_hash,
                "role": "admin",
                "classes": []  # Admins might not be assigned to any class
            }

            # Add the admin user to Firestore
            db.collection("users").add(admin_data)
            logger.info(f"Default admin user '{default_admin_username}' created successfully.")
            print(f"Default admin user '{default_admin_username}' created successfully.")
        else:
            logger.info("Admin user already exists. No action needed.")
            print("Admin user already exists. No action needed.")
    except Exception as e:
        logger.error(f"Error creating default admin: {str(e)}")
        print(f"Error creating default admin: {str(e)}")

if __name__ == "__main__":
    # Create default admin if none exists
    create_default_admin()
    
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)