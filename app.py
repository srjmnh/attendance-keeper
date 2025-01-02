import os
import base64
import json
import io
from datetime import datetime

import boto3
import cv2
import numpy as np
from PIL import Image, ImageEnhance
from flask import Flask, request, jsonify, render_template_string, send_file

# -------------------------------------------------------------------
# 1) AWS Rekognition Setup
# -------------------------------------------------------------------
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

# -------------------------------------------------------------------
# 2) Firebase Firestore Setup (Credentials from Base64 Env Var)
# -------------------------------------------------------------------
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

# -------------------------------------------------------------------
# 3) Flask App
# -------------------------------------------------------------------
app = Flask(__name__)

# -------------------------------------------------------------------
# 4) Image Enhancement Functions
# -------------------------------------------------------------------
def upscale_image(image_bytes, upscale_factor=2):
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    upscaled_image = cv2.resize(image, None, fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_CUBIC)
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

# -------------------------------------------------------------------
# 5) Simple Home Page (if you like)
# -------------------------------------------------------------------
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Face Recognition Home</title>
</head>
<body>
    <h1>Welcome to Face Recognition with AWS & Firebase Attendance!</h1>
    <p>Use the <strong>/register</strong> endpoint (POST) to register new faces.</p>
    <p>Use the <strong>/recognize</strong> endpoint (POST) to recognize faces.</p>
    <p>Visit <a href="/attendance">/attendance</a> for attendance management (filter, edit, export, import).</p>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

# -------------------------------------------------------------------
# 6) Register Endpoint (AWS Face Enrollment)
# -------------------------------------------------------------------
@app.route('/register', methods=['POST'])
def register():
    """
    Expects JSON:
    {
      "name": "Alice",
      "student_id": "12345",
      "image": "data:image/jpeg;base64,...."
    }
    """
    try:
        data = request.json
        name = data.get('name')
        student_id = data.get('student_id')
        image = data.get('image')

        if not name or not student_id or not image:
            return jsonify({"message": "Missing name, student_id, or image"}), 400

        sanitized_name = "".join(c if c.isalnum() or c in "_-." else "_" for c in name)

        # Decode base64
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

# -------------------------------------------------------------------
# 7) Recognize Endpoint (AWS Face Recognition) + Firestore Attendance
# -------------------------------------------------------------------
@app.route('/recognize', methods=['POST'])
def recognize():
    """
    Expects JSON:
    {
      "image": "data:image/jpeg;base64,....",
      "subject_id": "abc123" (optional if you want to record subject info)
    }
    """
    try:
        data = request.json
        image_data_str = data.get('image')
        subject_id = data.get('subject_id')  # optional

        if not image_data_str:
            return jsonify({"message": "No image provided"}), 400

        # Optionally fetch subject_name from a "subjects" collection if you store it
        # For demo, let's just store subject_id if provided:
        subject_name = ""
        if subject_id:
            subj_doc = db.collection("subjects").document(subject_id).get()
            if subj_doc.exists:
                subject_name = subj_doc.to_dict().get("name", "")
            else:
                subject_name = "Unknown Subject"

        # Decode base64
        image_bytes = base64.b64decode(image_data_str.split(",")[1])

        # Enhance
        image_bytes = upscale_image(image_bytes)
        image_bytes = denoise_image(image_bytes)
        image_bytes = equalize_image(image_bytes)

        # More brightness/contrast
        pil_img = Image.open(io.BytesIO(image_bytes))
        enhancer = ImageEnhance.Contrast(pil_img)
        pil_img = enhancer.enhance(1.5)
        enhancer = ImageEnhance.Brightness(pil_img)
        pil_img = enhancer.enhance(1.2)

        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG")
        final_enhanced_bytes = buf.getvalue()

        # Split into smaller grids
        regions = split_image(pil_img, grid_size=3)

        identified_people = []
        face_count = 0

        for region in regions:
            r_buf = io.BytesIO()
            region.save(r_buf, format="JPEG")
            region_bytes = r_buf.getvalue()

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
                cropped_bytes = c_buf.getvalue()

                # Search in Rekognition
                search_response = rekognition_client.search_faces_by_image(
                    CollectionId=COLLECTION_ID,
                    Image={'Bytes': cropped_bytes},
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
                    recognized_name, recognized_student_id = parts
                else:
                    recognized_name = ext_id
                    recognized_student_id = "Unknown"

                identified_people.append({
                    "name": recognized_name,
                    "student_id": recognized_student_id,
                    "confidence": confidence
                })

                # Log attendance in Firestore
                # You can customize fields as needed
                if recognized_student_id != "Unknown":
                    attendance_record = {
                        "student_id": recognized_student_id,
                        "name": recognized_name,
                        "timestamp": datetime.utcnow().isoformat(),
                        "subject_id": subject_id or "",
                        "subject_name": subject_name or "",
                        "status": "PRESENT"  # or "IN", or whatever logic you prefer
                    }
                    db.collection("attendance").add(attendance_record)

        return jsonify({
            "message": f"{face_count} face(s) detected in the photo.",
            "total_faces": face_count,
            "identified_people": identified_people
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------------------------------------------------------
# 8) Attendance Management Page (DataTables + Excel Import/Export)
# -------------------------------------------------------------------
import openpyxl
from openpyxl import Workbook

ATTENDANCE_PAGE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Attendance Management</title>
    <meta charset="UTF-8">
    <!-- DataTables CSS -->
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.4/css/jquery.dataTables.min.css">
    <style>
      body { font-family: Arial, sans-serif; margin: 20px; }
      .filters { margin-bottom: 20px; }
      .filters label { margin-right: 10px; }
      #attendanceTable { width: 100%; border-collapse: collapse; }
      #attendanceTable th, #attendanceTable td {
        padding: 8px; 
        border: 1px solid #ccc;
      }
      .save-btn, .download-btn, .upload-btn {
        margin: 10px 5px 10px 0;
        padding: 8px 16px;
      }
    </style>
</head>
<body>

<h1>Attendance Management</h1>

<div class="filters">
  <label>Student ID:
    <input type="text" id="filter_student_id" placeholder="e.g. 1234">
  </label>
  <label>Subject ID:
    <input type="text" id="filter_subject_id" placeholder="e.g. abc123">
  </label>
  <label>Start Date:
    <input type="date" id="filter_start">
  </label>
  <label>End Date:
    <input type="date" id="filter_end">
  </label>
  <button onclick="loadAttendance()">Apply Filters</button>
</div>

<table id="attendanceTable" class="display" style="width:100%">
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

<div>
  <button class="save-btn" onclick="saveEdits()">Save Changes</button>
  <button class="download-btn" onclick="downloadExcel()">Download Excel</button>

  <!-- Upload Excel form -->
  <input type="file" id="excelFile" accept=".xlsx">
  <button class="upload-btn" onclick="uploadExcel()">Upload Excel</button>
</div>

<!-- jQuery & DataTables JS -->
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>

<script>
let table;
let attendanceData = [];

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
      <td contenteditable="true" data-field="student_id">${record.student_id || ''}</td>
      <td contenteditable="true" data-field="name">${record.name || ''}</td>
      <td contenteditable="true" data-field="subject_id">${record.subject_id || ''}</td>
      <td contenteditable="true" data-field="subject_name">${record.subject_name || ''}</td>
      <td contenteditable="true" data-field="timestamp">${record.timestamp || ''}</td>
      <td contenteditable="true" data-field="status">${record.status || ''}</td>
    `;
    tbody.appendChild(row);
  });

  table = $('#attendanceTable').DataTable({
    paging: true,
    searching: false,
    info: false,
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

window.onload = loadAttendance;
</script>
</body>
</html>
"""

@app.route("/attendance")
def attendance_page():
    return render_template_string(ATTENDANCE_PAGE_HTML)

# -------------------------------------------------------------------
# 9) Attendance API Endpoints
# -------------------------------------------------------------------
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
        dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999)
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
        dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999)
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

    # Expecting columns in first row:
    # doc_id, student_id, name, subject_id, subject_name, timestamp, status
    headers = rows[0]
    expected = ("doc_id", "student_id", "name", "subject_id", "subject_name", "timestamp", "status")
    if headers != expected:
        return jsonify({"error": "Incorrect template format"}), 400

    for row in rows[1:]:
        doc_id, student_id, name, subject_id, subject_name, timestamp, status = row
        if doc_id:
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

# -------------------------------------------------------------------
# 10) Run the Flask app
# -------------------------------------------------------------------
if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
