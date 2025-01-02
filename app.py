import os
import base64
import json
import io
from datetime import datetime

import cv2
import numpy as np
from PIL import Image, ImageEnhance
from flask import Flask, request, jsonify, render_template_string, send_file

# 1) AWS Rekognition Setup
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

# 2) Firebase Firestore Setup
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

# 3) Flask App
app = Flask(__name__)

# 4) Image Enhancement Functions
def upscale_image(image_bytes, upscale_factor=2):
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    upscaled_image = cv2.resize(
        image, None, fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_CUBIC
    )
    _, upscaled_image_bytes = cv2.imencode('.jpg', upscaled_image)
    return upscaled_image_bytes.tobytes()

def denoise_image(image_bytes):
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    denoised_image = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
    _, denoised_image_bytes = cv2.imencode('.jpg', denoised_image)
    return denoised_image_bytes.tobytes()

def equalize_image(image_bytes):
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.equalizeHist(l)
    lab = cv2.merge((l, a, b))
    enhanced_image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    _, enhanced_image_bytes = cv2.imencode('.jpg', enhanced_image)
    return enhanced_image_bytes.tobytes()

def split_image(pil_image, grid_size=3):
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

# 5) Single HTML with 4 tabs: Register, Recognize, Subjects, Attendance
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Facial Recognition Attendance System</title>
  <!-- Bootstrap CSS (v5) -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <!-- DataTables CSS -->
  <link rel="stylesheet" href="https://cdn.datatables.net/1.13.4/css/jquery.dataTables.min.css">
  <style>
    body { margin: 20px; }
    .nav-tabs .nav-link { color: #555; }
    .nav-tabs .nav-link.active { color: #000; font-weight: bold; }
    .content-section { margin-top: 20px; }
    .form-label { font-weight: 500; }
    .form-control, .btn { margin-bottom: 10px; }
    @media (max-width: 576px) {
      /* Mobile-friendly adjustments */
      .content-section { margin-top: 10px; }
    }
    /* Table styling for attendance */
    #attendanceTable th, #attendanceTable td {
      vertical-align: middle;
    }
    #attendanceTable td[contenteditable="true"] {
      background-color: #fcf8e3; /* highlight color for editable cells */
    }
  </style>
</head>
<body class="container">

<h1 class="mt-4">Facial Recognition Attendance System</h1>

<!-- Nav Tabs -->
<ul class="nav nav-tabs" id="myTab" role="tablist">
  <li class="nav-item" role="presentation">
    <button class="nav-link active" id="register-tab" data-bs-toggle="tab" data-bs-target="#register" type="button" role="tab">
      Register
    </button>
  </li>
  <li class="nav-item" role="presentation">
    <button class="nav-link" id="recognize-tab" data-bs-toggle="tab" data-bs-target="#recognize" type="button" role="tab">
      Recognize
    </button>
  </li>
  <li class="nav-item" role="presentation">
    <button class="nav-link" id="subjects-tab" data-bs-toggle="tab" data-bs-target="#subjects" type="button" role="tab">
      Subjects
    </button>
  </li>
  <li class="nav-item" role="presentation">
    <button class="nav-link" id="attendance-tab" data-bs-toggle="tab" data-bs-target="#attendance" type="button" role="tab">
      Attendance
    </button>
  </li>
</ul>

<div class="tab-content" id="myTabContent">
  <!-- REGISTER TAB -->
  <div class="tab-pane fade show active content-section" id="register" role="tabpanel" aria-labelledby="register-tab">
    <h3>Register a Face</h3>
    <label class="form-label">Name</label>
    <input type="text" id="reg_name" class="form-control" placeholder="Enter Name">
    <label class="form-label">Student ID</label>
    <input type="text" id="reg_student_id" class="form-control" placeholder="Enter Student ID">
    <label class="form-label">Image</label>
    <input type="file" id="reg_image" class="form-control" accept="image/*">
    <button onclick="registerFace()" class="btn btn-primary">Register</button>
    <div id="register_result" class="alert alert-info mt-3" style="display:none;"></div>
  </div>

  <!-- RECOGNIZE TAB -->
  <div class="tab-pane fade content-section" id="recognize" role="tabpanel" aria-labelledby="recognize-tab">
    <h3>Recognize a Face</h3>
    <label class="form-label">Subject (optional):</label>
    <select id="rec_subject_select" class="form-control">
      <option value="">-- No Subject --</option>
    </select>
    <label class="form-label">Image</label>
    <input type="file" id="rec_image" class="form-control" accept="image/*">
    <button onclick="recognizeFace()" class="btn btn-success">Recognize</button>
    <div id="recognize_result" class="alert alert-info mt-3" style="display:none;"></div>
  </div>

  <!-- SUBJECTS TAB -->
  <div class="tab-pane fade content-section" id="subjects" role="tabpanel" aria-labelledby="subjects-tab">
    <h3>Manage Subjects</h3>
    <label class="form-label">New Subject Name:</label>
    <input type="text" id="subject_name" class="form-control" placeholder="e.g. Mathematics">
    <button onclick="addSubject()" class="btn btn-primary">Add Subject</button>
    <div id="subject_result" class="alert alert-info mt-3" style="display:none;"></div>
    <hr>
    <h5>Existing Subjects</h5>
    <ul id="subjects_list"></ul>
  </div>

  <!-- ATTENDANCE TAB -->
  <div class="tab-pane fade content-section" id="attendance" role="tabpanel" aria-labelledby="attendance-tab">
    <h3>Attendance Records</h3>
    <div class="row mb-3">
      <div class="col-md-3">
        <label class="form-label">Student ID</label>
        <input type="text" id="filter_student_id" class="form-control" placeholder="e.g. 1234">
      </div>
      <div class="col-md-3">
        <label class="form-label">Subject ID</label>
        <input type="text" id="filter_subject_id" class="form-control" placeholder="e.g. abc123">
      </div>
      <div class="col-md-3">
        <label class="form-label">Start Date</label>
        <input type="date" id="filter_start" class="form-control">
      </div>
      <div class="col-md-3">
        <label class="form-label">End Date</label>
        <input type="date" id="filter_end" class="form-control">
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
      <label class="form-label d-block mt-3">Upload Excel (template must match columns):</label>
      <input type="file" id="excelFile" accept=".xlsx" class="form-control mb-2">
      <button class="btn btn-dark" onclick="uploadExcel()">Upload Excel</button>
    </div>
  </div>
</div>

<!-- Bootstrap JS + Dependencies -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<!-- jQuery & DataTables JS -->
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>

<script>
/**
 * GLOBALS
 */
let table;
let attendanceData = [];

/**
 * Convert file to Base64
 */
function getBase64(file, callback) {
  const reader = new FileReader();
  reader.readAsDataURL(file);
  reader.onload = () => callback(reader.result);
  reader.onerror = (error) => console.error('Error: ', error);
}

/**
 * REGISTER a Face => /register (POST)
 */
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

/**
 * RECOGNIZE a Face => /recognize (POST)
 */
function recognizeFace() {
  const file = document.getElementById('rec_image').files[0];
  const subjectId = document.getElementById('rec_subject_select').value;

  if (!file) {
    alert('Please select an image to recognize.');
    return;
  }

  getBase64(file, (base64Str) => {
    fetch('/recognize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image: base64Str,
        subject_id: subjectId
      })
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

/**
 * SUBJECTS
 */
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
    // rec_subject_select
    const select = document.getElementById('rec_subject_select');
    select.innerHTML = '<option value="">-- No Subject --</option>';
    (data.subjects || []).forEach(sub => {
      const option = document.createElement('option');
      option.value = sub.id;
      option.textContent = sub.name;
      select.appendChild(option);
    });
    // subjects_list
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

/**
 * ATTENDANCE
 */
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
    .then(response => response.json())
    .then(data => {
      attendanceData = data;
      renderTable(attendanceData);
    })
    .catch(err => console.error(err));
}

function renderTable(data) {
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

  table = $('#attendanceTable').DataTable({
    paging: true,
    searching: false,
    info: false,
    responsive: true
  });
}

function saveEdits() {
  const updatedRecords = [];
  const rows = document.querySelectorAll('#attendanceTable tbody tr');

  rows.forEach(row => {
    const cells = row.querySelectorAll('td');
    const doc_id = cells[0].textContent.trim();
    const student_id = cells[1].textContent.trim();
    const name = cells[2].textContent.trim();
    const subject_id = cells[3].textContent.trim();
    const subject_name = cells[4].textContent.trim();
    const timestamp = cells[5].textContent.trim();
    const status = cells[6].textContent.trim();

    updatedRecords.push({
      doc_id, student_id, name, subject_id, subject_name, timestamp, status
    });
  });

  fetch('/api/attendance/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ records: updatedRecords })
  })
  .then(res => res.json())
  .then(resp => {
    alert(resp.message || 'Attendance updated!');
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

// On page load, load subjects
document.addEventListener('DOMContentLoaded', () => {
  loadSubjects();
});
</script>
</body>
</html>
"""

# 6) Routes for Single-Page UI
@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

# 7) Subjects
@app.route("/add_subject", methods=["POST"])
def add_subject():
    data = request.json
    subject_name = data.get("subject_name")
    if not subject_name:
        return jsonify({"error": "No subject_name provided"}), 400

    doc_ref = db.collection("subjects").document()
    subject_data = {
        "name": subject_name.strip(),
        "created_at": datetime.utcnow().isoformat()
    }
    doc_ref.set(subject_data)
    return jsonify({"message": f"Subject '{subject_name}' added successfully!"}), 200

@app.route("/get_subjects", methods=["GET"])
def get_subjects():
    subjects_col = db.collection("subjects").stream()
    subjects_list = []
    for doc in subjects_col:
        data = doc.to_dict()
        subjects_list.append({
            "id": doc.id,
            "name": data.get("name", "")
        })
    return jsonify({"subjects": subjects_list}), 200

# 8) Register a Face
@app.route("/register", methods=["POST"])
def register_face():
    """
    JSON: { "name": "Alice", "student_id": "12345", "image": "data:image/jpeg;base64,..." }
    """
    try:
        data = request.json
        name = data.get('name')
        student_id = data.get('student_id')
        image = data.get('image')

        if not name or not student_id or not image:
            return jsonify({"message": "Missing name, student_id, or image"}), 400

        sanitized_name = "".join(c if c.isalnum() or c in "_-." else "_" for c in name)
        image_data = image.split(",")[1]
        image_bytes = base64.b64decode(image_data)

        external_image_id = f"{sanitized_name}_{student_id}"
        response = rekognition_client.index_faces(
            CollectionId=COLLECTION_ID,
            Image={'Bytes': image_bytes},
            ExternalImageId=external_image_id,
            DetectionAttributes=['ALL'],
            QualityFilter='AUTO'
        )
        if not response.get('FaceRecords'):
            return jsonify({"message": "No face detected in the image"}), 400

        return jsonify({"message": f"Student {name} with ID {student_id} registered successfully!"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 9) Recognize a Face + Log Attendance
@app.route("/recognize", methods=["POST"])
def recognize():
    """
    JSON: { "image": "data:image/jpeg;base64,...", "subject_id": "docID" (optional) }
    """
    try:
        data = request.json
        image_str = data.get('image')
        subject_id = data.get('subject_id') or ""

        if not image_str:
            return jsonify({"message": "No image provided"}), 400

        # Attempt to fetch subject info if subject_id is provided
        subject_name = ""
        if subject_id:
            subj_doc = db.collection("subjects").document(subject_id).get()
            if subj_doc.exists:
                subject_name = subj_doc.to_dict().get("name", "")
            else:
                subject_name = "Unknown Subject"

        # Enhance image
        raw_bytes = base64.b64decode(image_str.split(",")[1])
        raw_bytes = upscale_image(raw_bytes)
        raw_bytes = denoise_image(raw_bytes)
        raw_bytes = equalize_image(raw_bytes)

        pil_img = Image.open(io.BytesIO(raw_bytes))
        # More brightness/contrast
        enhancer = ImageEnhance.Contrast(pil_img)
        pil_img = enhancer.enhance(1.5)
        enhancer = ImageEnhance.Brightness(pil_img)
        pil_img = enhancer.enhance(1.2)

        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG")
        final_bytes = buf.getvalue()

        # Split into smaller grids
        regions = split_image(pil_img, grid_size=3)

        identified_people = []
        face_count = 0

        for region in regions:
            region_buf = io.BytesIO()
            region.save(region_buf, format="JPEG")
            region_bytes = region_buf.getvalue()

            detect_response = rekognition_client.detect_faces(
                Image={'Bytes': region_bytes},
                Attributes=['ALL']
            )
            faces = detect_response.get('FaceDetails', [])
            face_count += len(faces)

            for face in faces:
                bbox = face['BoundingBox']
                w, h = region.size
                left = int(bbox['Left'] * w)
                top = int(bbox['Top'] * h)
                right = int((bbox['Left'] + bbox['Width']) * w)
                bottom = int((bbox['Top'] + bbox['Height']) * h)

                cropped_face = region.crop((left, top, right, bottom))
                c_buf = io.BytesIO()
                cropped_face.save(c_buf, format="JPEG")
                cropped_face_bytes = c_buf.getvalue()

                # search in Rekognition
                search_response = rekognition_client.search_faces_by_image(
                    CollectionId=COLLECTION_ID,
                    Image={'Bytes': cropped_face_bytes},
                    MaxFaces=1,
                    FaceMatchThreshold=60
                )
                face_matches = search_response.get('FaceMatches', [])
                if not face_matches:
                    identified_people.append({
                        "message": "Face not recognized",
                        "confidence": "N/A"
                    })
                    continue

                match = face_matches[0]
                ext_id = match['Face']['ExternalImageId']  # e.g. "Alice_12345"
                confidence = match['Face']['Confidence']

                parts = ext_id.split("_", 1)
                if len(parts) == 2:
                    recognized_name, recognized_id = parts
                else:
                    recognized_name = ext_id
                    recognized_id = "Unknown"

                identified_people.append({
                    "name": recognized_name,
                    "student_id": recognized_id,
                    "confidence": f"{confidence:.2f}"
                })

                # Log attendance if recognized
                if recognized_id != "Unknown":
                    doc = {
                        "student_id": recognized_id,
                        "name": recognized_name,
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

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 10) Attendance Endpoints (GET/POST for listing, updating, Excel import/export)
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
        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.where("timestamp", ">=", dt_start.isoformat())
    if end_date:
        dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
        query = query.where("timestamp", "<=", dt_end.isoformat())

    results = query.stream()
    attendance_list = []
    for doc in results:
        doc_data = doc.to_dict()
        doc_data["doc_id"] = doc.id
        attendance_list.append(doc_data)

    return jsonify(attendance_list)

@app.route("/api/attendance/update", methods=["POST"])
def update_attendance():
    data = request.json
    records = data.get("records", [])
    for rec in records:
        doc_id = rec.get("doc_id")
        if not doc_id:
            continue
        update_data = {
            "student_id": rec.get("student_id", ""),
            "name": rec.get("name", ""),
            "subject_id": rec.get("subject_id", ""),
            "subject_name": rec.get("subject_name", ""),
            "timestamp": rec.get("timestamp", ""),
            "status": rec.get("status", ""),
        }
        db.collection("attendance").document(doc_id).update(update_data)
    return jsonify({"message": "Attendance records updated successfully."})

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
        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.where("timestamp", ">=", dt_start.isoformat())
    if end_date:
        dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
        query = query.where("timestamp", "<=", dt_end.isoformat())

    results = query.stream()
    attendance_list = []
    for doc in results:
        doc_data = doc.to_dict()
        doc_data["doc_id"] = doc.id
        attendance_list.append(doc_data)

    wb = Workbook()
    ws = wb.active
    ws.title = "Attendance"
    headers = ["doc_id", "student_id", "name", "subject_id", "subject_name", "timestamp", "status"]
    ws.append(headers)

    for record in attendance_list:
        row = [
            record.get("doc_id", ""),
            record.get("student_id", ""),
            record.get("name", ""),
            record.get("subject_id", ""),
            record.get("subject_name", ""),
            record.get("timestamp", ""),
            record.get("status", ""),
        ]
        ws.append(row)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        attachment_filename="attendance.xlsx",
    )

@app.route("/api/attendance/upload", methods=["POST"])
def upload_attendance_excel():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename.endswith(".xlsx"):
        return jsonify({"error": "Please upload a .xlsx file"}), 400

    wb = openpyxl.load_workbook(file)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    # columns: doc_id, student_id, name, subject_id, subject_name, timestamp, status
    expected_headers = ("doc_id", "student_id", "name", "subject_id", "subject_name", "timestamp", "status")
    if rows and rows[0] != expected_headers:
        return jsonify({"error": "Incorrect template format"}), 400

    for row in rows[1:]:
        doc_id, student_id, name, subject_id, subject_name, timestamp, status = row
        if doc_id:
            # update existing
            update_data = {
                "student_id": student_id or "",
                "name": name or "",
                "subject_id": subject_id or "",
                "subject_name": subject_name or "",
                "timestamp": timestamp or "",
                "status": status or "",
            }
            db.collection("attendance").document(doc_id).set(update_data, merge=True)
        else:
            # create new doc
            new_data = {
                "student_id": student_id or "",
                "name": name or "",
                "subject_id": subject_id or "",
                "subject_name": subject_name or "",
                "timestamp": timestamp or "",
                "status": status or "",
            }
            db.collection("attendance").add(new_data)

    return jsonify({"message": "Excel data imported successfully."})

# 11) Run Flask
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
