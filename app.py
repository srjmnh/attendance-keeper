import os
import base64
import json
import io
from datetime import datetime

from flask import Flask, request, jsonify, render_template_string, send_file
import firebase_admin
from firebase_admin import credentials, firestore

import google.generativeai as genai

import boto3
import cv2
import numpy as np
from PIL import Image

# ------------------------------------------------------
# 1) FLASK SETUP
# ------------------------------------------------------
app = Flask(__name__)

# ------------------------------------------------------
# 2) AWS REKOGNITION CONFIG
# ------------------------------------------------------
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

def create_collection_if_not_exists():
    try:
        rekognition_client.create_collection(CollectionId=COLLECTION_ID)
        print(f"Collection '{COLLECTION_ID}' created.")
    except rekognition_client.exceptions.ResourceAlreadyExistsException:
        print(f"Collection '{COLLECTION_ID}' already exists.")

create_collection_if_not_exists()

# ------------------------------------------------------
# 3) FIREBASE FIRESTORE SETUP
# ------------------------------------------------------
encoded_json = os.getenv("FIREBASE_ADMIN_CREDENTIALS_BASE64")
if not encoded_json:
    raise ValueError("FIREBASE_ADMIN_CREDENTIALS_BASE64 not set.")

decoded_json = base64.b64decode(encoded_json)
cred_dict = json.loads(decoded_json)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)
db = firestore.client()

# ------------------------------------------------------
# 4) GEMINI CHATBOT CONFIG
# ------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

genai.configure(api_key=GEMINI_API_KEY)
# If you lack "gemini-1.5-flash", you can swap to "models/chat-bison-001"
gemini_model = genai.GenerativeModel("models/gemini-1.5-flash")

# We'll keep a short conversation memory
MAX_MEMORY = 20
conversation_memory = []

# System prompt telling Gemini how to classify or handle actions
system_context = """You are a helpful, somewhat witty AI that:
1) Does normal chat or help about the system.
2) Performs Firestore queries/updates if user requests data changes or analytics.

**Output** must be JSON if an action is needed, like:
{
  "type": "firestore",
  "action": "query_attendance_lowest",
  "subject": "physics"
}
OR:
{
  "type": "firestore",
  "action": "update_subject_name",
  "old_name": "Physics",
  "new_name": "Advanced Physics"
}
If it's normal talk => {"type":"casual"}.

System also manages a Facial Recognition Attendance system with:
- AWS Rekognition
- Firestore attendance logs
- Subjects
- A UI with tabs: Register, Recognize, Subjects, Attendance
**We** can retrieve or modify data in Firestore if asked. 
"""

# Add system prompt as initial memory
conversation_memory.append({"role":"system","content":system_context})

# ------------------------------------------------------
# 5) OPTIONAL IMAGE ENHANCEMENT FUNCTIONS
# ------------------------------------------------------
def upscale_image(image_bytes, factor=2):
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    upscaled = cv2.resize(img, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
    _, upscaled_bytes = cv2.imencode('.jpg', upscaled)
    return upscaled_bytes.tobytes()

def denoise_image(image_bytes):
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    denoised = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
    _, denoised_bytes = cv2.imencode('.jpg', denoised)
    return denoised_bytes.tobytes()

def equalize_image(image_bytes):
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l,a,b = cv2.split(lab)
    l = cv2.equalizeHist(l)
    merged = cv2.merge((l,a,b))
    eq_img = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    _, eq_bytes = cv2.imencode('.jpg', eq_img)
    return eq_bytes.tobytes()

def split_image(pil_image, grid_size=3):
    w,h = pil_image.size
    rw = w // grid_size
    rh = h // grid_size
    regions = []
    for row in range(grid_size):
        for col in range(grid_size):
            left = col * rw
            top = row * rh
            right = (col+1)*rw
            bottom = (row+1)*rh
            region = pil_image.crop((left, top, right, bottom))
            regions.append(region)
    return regions

# ------------------------------------------------------
# 6) HELPER: CLASSIFICATION for Firestore Actions
# ------------------------------------------------------
def classify_with_gemini(prompt):
    """
    Ask Gemini to produce JSON describing 'type' and 'action' if it's a Firestore request, else 'casual'.
    """
    classification_system = "You are a JSON classifier:\n" + system_context
    conversation_str = f"System: {classification_system}\nUser: {prompt}\n"

    resp = gemini_model.generate_content(conversation_str)
    if not resp.candidates:
        return {"type":"casual"}
    text = "".join(part.text for part in resp.candidates[0].content.parts).strip()
    # remove code fences
    if text.startswith("```"):
        text = text.strip("```").strip()
    try:
        data = json.loads(text)
        if "type" not in data:
            data["type"] = "casual"
        return data
    except:
        return {"type":"casual"}

# ------------------------------------------------------
# 7) FIRESTORE ACTIONS
# ------------------------------------------------------
def query_attendance_lowest(subject):
    """
    Finds the student with the least attendance for a given subject.
    We'll do a naive approach: group by 'student_id' in 'attendance' collection 
    where subject_id=subject. 
    Then pick min by count.
    """
    docs = db.collection("attendance").where("subject_id","==",subject).stream()
    counts = {}
    for d in docs:
        rec = d.to_dict()
        sid = rec.get("student_id","Unknown")
        counts[sid] = counts.get(sid,0)+1
    if not counts:
        return f"No attendance records found for subject '{subject}'."
    min_sid = min(counts, key=counts.get)
    min_val = counts[min_sid]
    return f"Student {min_sid} has the lowest attendance in '{subject}', with {min_val} records."

def update_subject_name(old_name,new_name):
    """
    Finds all 'subjects' docs with name=old_name, updates them to name=new_name.
    """
    docs = db.collection("subjects").where("name","==",old_name).stream()
    found=False
    for d in docs:
        d.reference.update({"name":new_name})
        found=True
    if found:
        return f"Subject '{old_name}' updated to '{new_name}'."
    else:
        return f"No subject named '{old_name}' found."

# ------------------------------------------------------
# 8) MAIN /process_prompt ENDPOINT
# ------------------------------------------------------
@app.route("/process_prompt", methods=["POST"])
def process_prompt():
    data = request.json
    user_prompt = data.get("prompt","").strip()
    if not user_prompt:
        return jsonify({"error":"No prompt"}),400

    # add user to memory
    conversation_memory.append({"role":"user","content":user_prompt})

    # classify
    classification = classify_with_gemini(user_prompt)
    if classification.get("type") == "firestore":
        action = classification.get("action")
        if action == "query_attendance_lowest":
            subj = classification.get("subject","")
            if not subj:
                assistant_reply = "Need a 'subject' to find the lowest attendance."
            else:
                assistant_reply = query_attendance_lowest(subj)
        elif action == "update_subject_name":
            old_name = classification.get("old_name","")
            new_name = classification.get("new_name","")
            if not old_name or not new_name:
                assistant_reply = "Need old_name and new_name to update the subject."
            else:
                assistant_reply = update_subject_name(old_name,new_name)
        else:
            assistant_reply = f"Unrecognized Firestore action: {action}"
    else:
        # casual talk => build conversation str
        conv_str = ""
        for msg in conversation_memory:
            if msg["role"]=="system":
                conv_str += f"System: {msg['content']}\n"
            elif msg["role"]=="user":
                conv_str += f"User: {msg['content']}\n"
            else:
                conv_str += f"Assistant: {msg['content']}\n"

        resp = gemini_model.generate_content(conv_str)
        if not resp.candidates:
            assistant_reply = "Hmm, I'm having trouble responding now."
        else:
            assistant_reply = "".join(part.text for part in resp.candidates[0].content.parts).strip()

    # add assistant reply to memory
    conversation_memory.append({"role":"assistant","content":assistant_reply})

    # trim memory
    if len(conversation_memory)>MAX_MEMORY:
        conversation_memory.pop(0)

    return jsonify({"message": assistant_reply})

# ------------------------------------------------------
# 9) The Single-Page UI for Register/Recognize/Subjects/Attendance + Chat
# ------------------------------------------------------
INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Facial Recognition + Gemini Analytics</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <!-- Bootstrap + DataTables -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"/>
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.4/css/jquery.dataTables.min.css" />

    <style>
      body { margin:20px; }
      .nav-tabs .nav-link { color:#555; }
      .nav-tabs .nav-link.active { color:#000; font-weight:bold; }
      #chatbotToggle {
        position: fixed; bottom:20px; right:20px; z-index:999;
        background-color:#0d6efd; color:#fff; border:none; border-radius:50%;
        width:50px; height:50px; font-size:22px; cursor:pointer;
        display:flex; align-items:center; justify-content:center;
      }
      #chatbotToggle:hover { background-color:#0b5ed7; }
      #chatbotWindow {
        position:fixed; bottom:80px; right:20px; width:300px; max-height:400px;
        border:1px solid #ccc; border-radius:10px; background-color:#fff;
        box-shadow:0 0 10px rgba(0,0,0,0.2); display:none; flex-direction:column; z-index:1000;
      }
      #chatHeader {
        background-color:#0d6efd; color:#fff; padding:10px; border-radius:10px 10px 0 0; font-weight:bold;
        display:flex; justify-content:space-between; align-items:center;
      }
      #chatHeader .close-btn {
        background:none; border:none; color:#fff; font-weight:bold; cursor:pointer; font-size:16px;
      }
      #chatMessages { flex:1; overflow-y:auto; padding:10px; font-size:14px; }
      .message { margin-bottom:10px; }
      .message.user { text-align:right; }
      .message.assistant { text-align:left; color:#333; }
      #chatInputArea { display:flex; border-top:1px solid #ddd; }
      #chatInput {
        flex:1; padding:8px; border:none; outline:none; font-size:14px;
      }
      #chatSendBtn {
        background-color:#0d6efd; color:#fff; border:none; padding:0 15px; cursor:pointer;
      }
      #chatSendBtn:hover { background-color:#0b5ed7; }
      #attendanceTable td[contenteditable="true"] { background-color:#fcf8e3; }
    </style>
</head>
<body class="container">

<h1 class="my-4">Facial Recognition + Gemini Analytics</h1>

<ul class="nav nav-tabs">
  <li class="nav-item">
    <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#register">Register</button>
  </li>
  <li class="nav-item">
    <button class="nav-link" data-bs-toggle="tab" data-bs-target="#recognize">Recognize</button>
  </li>
  <li class="nav-item">
    <button class="nav-link" data-bs-toggle="tab" data-bs-target="#subjects">Subjects</button>
  </li>
  <li class="nav-item">
    <button class="nav-link" data-bs-toggle="tab" data-bs-target="#attendance">Attendance</button>
  </li>
</ul>

<div class="tab-content">
  <div class="tab-pane fade show active" id="register" style="margin-top:20px;">
    <h3>Register a Face</h3>
    <label>Name: <input type="text" id="reg_name" class="form-control" /></label><br/>
    <label>Student ID: <input type="text" id="reg_student_id" class="form-control" /></label><br/>
    <label>Image: <input type="file" id="reg_image" accept="image/*" class="form-control" /></label><br/>
    <button class="btn btn-primary" onclick="registerFace()">Register</button>
    <div id="register_result" class="alert alert-info mt-2" style="display:none;"></div>
  </div>

  <div class="tab-pane fade" id="recognize" style="margin-top:20px;">
    <h3>Recognize a Face</h3>
    <label>Subject (optional): 
      <select id="rec_subject_select" class="form-control">
        <option value="">-- None --</option>
      </select>
    </label><br/>
    <label>Image: <input type="file" id="rec_image" accept="image/*" class="form-control" /></label><br/>
    <button class="btn btn-success" onclick="recognizeFace()">Recognize</button>
    <div id="recognize_result" class="alert alert-info mt-2" style="display:none;"></div>
  </div>

  <div class="tab-pane fade" id="subjects" style="margin-top:20px;">
    <h3>Manage Subjects</h3>
    <label>New Subject Name: <input type="text" id="subject_name" class="form-control" /></label><br/>
    <button class="btn btn-primary" onclick="addSubject()">Add Subject</button>
    <div id="subject_result" class="alert alert-info mt-2" style="display:none;"></div>
    <hr/>
    <h5>Existing Subjects</h5>
    <ul id="subjects_list"></ul>
  </div>

  <div class="tab-pane fade" id="attendance" style="margin-top:20px;">
    <h3>Attendance Records</h3>
    <div class="row mb-3">
      <div class="col-md-3">
        <label>Student ID: <input type="text" id="filter_student_id" class="form-control" /></label>
      </div>
      <div class="col-md-3">
        <label>Subject ID: <input type="text" id="filter_subject_id" class="form-control" /></label>
      </div>
      <div class="col-md-3">
        <label>Start Date: <input type="date" id="filter_start" class="form-control" /></label>
      </div>
      <div class="col-md-3">
        <label>End Date: <input type="date" id="filter_end" class="form-control" /></label>
      </div>
    </div>
    <button class="btn btn-info" onclick="loadAttendance()">Apply Filters</button>
    <table id="attendanceTable" class="display table table-striped w-100 mt-3">
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
      <label class="d-block mt-3">Upload Excel:</label>
      <input type="file" id="excelFile" accept=".xlsx" class="form-control mb-2"/>
      <button class="btn btn-dark" onclick="uploadExcel()">Upload Excel</button>
    </div>
  </div>
</div>

<!-- Chatbot Toggle Button -->
<button id="chatbotToggle">💬</button>

<!-- Chatbot Window -->
<div id="chatbotWindow">
  <div id="chatHeader">
    <span>Gemini Chat</span>
    <button class="close-btn" id="chatCloseBtn">X</button>
  </div>
  <div id="chatMessages"></div>
  <div id="chatInputArea">
    <input type="text" id="chatInput" placeholder="Type a message..."/>
    <button id="chatSendBtn">Send</button>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
<script>
  // Chat toggle
  const toggleBtn = document.getElementById('chatbotToggle');
  const chatWindow = document.getElementById('chatbotWindow');
  const chatCloseBtn = document.getElementById('chatCloseBtn');
  const chatMessages = document.getElementById('chatMessages');
  const chatInput = document.getElementById('chatInput');
  const chatSendBtn = document.getElementById('chatSendBtn');

  toggleBtn.addEventListener('click', () => {
    chatWindow.style.display = (chatWindow.style.display==='none'||chatWindow.style.display==='') ? 'flex' : 'none';
  });
  chatCloseBtn.addEventListener('click', () => {
    chatWindow.style.display = 'none';
  });

  function addMessage(text, sender) {
    const div = document.createElement('div');
    div.classList.add('message', sender);
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function sendMessage() {
    const userText = chatInput.value.trim();
    if (!userText) return;
    addMessage(userText, 'user');
    chatInput.value = '';

    fetch('/process_prompt', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({prompt:userText})
    })
    .then(r=>r.json())
    .then(d=>{
      addMessage(d.message, 'assistant');
    })
    .catch(e=>{
      addMessage("Error or server not available", 'assistant');
      console.error(e);
    });
  }

  chatSendBtn.addEventListener('click', sendMessage);
  chatInput.addEventListener('keydown', (e)=>{
    if(e.key==='Enter'){
      e.preventDefault();
      sendMessage();
    }
  });

  // Register
  function getBase64(file, callback) {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = ()=> callback(reader.result);
    reader.onerror = (e)=> console.error(e);
  }

  function registerFace(){
    const name = document.getElementById('reg_name').value.trim();
    const sid = document.getElementById('reg_student_id').value.trim();
    const file = document.getElementById('reg_image').files[0];
    if(!name||!sid||!file){
      alert("Need name, student ID, and image.");
      return;
    }
    getBase64(file,(base64Str)=>{
      fetch('/register',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({name,s tudent_id:sid, image:base64Str})
      })
      .then(r=>r.json())
      .then(d=>{
        const div = document.getElementById('register_result');
        div.style.display='block';
        div.textContent= d.message|| d.error|| JSON.stringify(d);
      })
      .catch(e=>console.error(e));
    });
  }

  // Recognize
  function recognizeFace(){
    const file = document.getElementById('rec_image').files[0];
    const subj = document.getElementById('rec_subject_select').value;
    if(!file){
      alert("Please select an image for recognition");
      return;
    }
    getBase64(file,(b64)=>{
      fetch('/recognize',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({image:b64, subject_id:subj})
      })
      .then(r=>r.json())
      .then(d=>{
        const div = document.getElementById('recognize_result');
        div.style.display='block';
        let text = d.message || d.error || JSON.stringify(d);
        if(d.identified_people){
          text += "\\n\\nIdentified People:\\n";
          d.identified_people.forEach(p=>{
            text += `- ${p.name || "Unknown"} (ID: ${p.student_id||"N/A"}), Confidence: ${p.confidence}\\n`;
          });
        }
        div.textContent= text;
      })
      .catch(e=>console.error(e));
    });
  }

  // Subjects
  function addSubject(){
    const subjectName = document.getElementById('subject_name').value.trim();
    if(!subjectName){
      alert("Please enter a subject name.");
      return;
    }
    fetch('/add_subject',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({subject_name: subjectName})
    })
    .then(r=>r.json())
    .then(d=>{
      const div = document.getElementById('subject_result');
      div.style.display='block';
      div.textContent= d.message|| d.error|| JSON.stringify(d);
      document.getElementById('subject_name').value='';
      loadSubjects();
    })
    .catch(e=>console.error(e));
  }

  function loadSubjects(){
    fetch('/get_subjects')
    .then(r=>r.json())
    .then(d=>{
      const select = document.getElementById('rec_subject_select');
      select.innerHTML='<option value="">-- None --</option>';
      (d.subjects||[]).forEach(sub=>{
        const opt = document.createElement('option');
        opt.value=sub.id;
        opt.textContent=sub.name;
        select.appendChild(opt);
      });
      // show list
      const ul = document.getElementById('subjects_list');
      if(ul){
        ul.innerHTML='';
        (d.subjects||[]).forEach(sub=>{
          const li = document.createElement('li');
          li.textContent=`ID:${sub.id}, Name:${sub.name}`;
          ul.appendChild(li);
        });
      }
    })
    .catch(e=>console.error(e));
  }

  // Attendance
  let table;
  let attendanceData=[];
  function loadAttendance(){
    const stid= document.getElementById('filter_student_id').value.trim();
    const sbjid= document.getElementById('filter_subject_id').value.trim();
    const start= document.getElementById('filter_start').value;
    const end= document.getElementById('filter_end').value;

    let url='/api/attendance?';
    if(stid) url+='student_id='+stid+'&';
    if(sbjid) url+='subject_id='+sbjid+'&';
    if(start) url+='start_date='+start+'&';
    if(end) url+='end_date='+end+'&';

    fetch(url)
    .then(r=>r.json())
    .then(d=>{
      attendanceData=d;
      renderAttendanceTable(attendanceData);
    })
    .catch(e=>console.error(e));
  }

  function renderAttendanceTable(data){
    const tbl = document.getElementById('attendanceTable');
    if($.fn.DataTable.isDataTable(tbl)){
      $(tbl).DataTable().clear().destroy();
    }
    const tbody= tbl.querySelector('tbody');
    tbody.innerHTML='';
    data.forEach(rec=>{
      const tr = document.createElement('tr');
      tr.innerHTML=`
        <td>${rec.doc_id||''}</td>
        <td contenteditable="true">${rec.student_id||''}</td>
        <td contenteditable="true">${rec.name||''}</td>
        <td contenteditable="true">${rec.subject_id||''}</td>
        <td contenteditable="true">${rec.subject_name||''}</td>
        <td contenteditable="true">${rec.timestamp||''}</td>
        <td contenteditable="true">${rec.status||''}</td>`;
      tbody.appendChild(tr);
    });
    $(tbl).DataTable({paging:true, searching:false, info:false, responsive:true});
  }

  function saveEdits(){
    const tbl = document.getElementById('attendanceTable');
    const rows = tbl.querySelectorAll('tbody tr');
    const updatedRecords=[];
    rows.forEach(r=>{
      const cells = r.querySelectorAll('td');
      const doc_id=cells[0].textContent.trim();
      const student_id=cells[1].textContent.trim();
      const name=cells[2].textContent.trim();
      const subject_id=cells[3].textContent.trim();
      const subject_name=cells[4].textContent.trim();
      const timestamp=cells[5].textContent.trim();
      const status=cells[6].textContent.trim();
      updatedRecords.push({doc_id, student_id, name, subject_id, subject_name, timestamp, status});
    });
    fetch('/api/attendance/update',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({records:updatedRecords})
    })
    .then(r=>r.json())
    .then(d=>{
      alert(d.message || JSON.stringify(d));
    })
    .catch(e=>console.error(e));
  }

  function downloadExcel(){
    const stid= document.getElementById('filter_student_id').value.trim();
    const sbjid= document.getElementById('filter_subject_id').value.trim();
    const start= document.getElementById('filter_start').value;
    const end= document.getElementById('filter_end').value;
    let url='/api/attendance/download?';
    if(stid) url+='student_id='+stid+'&';
    if(sbjid) url+='subject_id='+sbjid+'&';
    if(start) url+='start_date='+start+'&';
    if(end) url+='end_date='+end+'&';
    window.location.href=url;
  }

  function downloadTemplate(){
    window.location.href='/api/attendance/template';
  }

  function uploadExcel(){
    const fileInput= document.getElementById('excelFile');
    if(!fileInput.files.length){
      alert("Please select a .xlsx file.");
      return;
    }
    const file= fileInput.files[0];
    const fd= new FormData();
    fd.append('file', file);

    fetch('/api/attendance/upload',{
      method:'POST',
      body:fd
    })
    .then(r=>r.json())
    .then(d=>{
      alert(d.message||d.error||'Upload done');
      loadAttendance();
    })
    .catch(e=>console.error(e));
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    loadSubjects();
  });
</script>
"""

@app.route("/", methods=["GET"])
def index():
    # Return the big single-page HTML
    return INDEX_HTML

# ------------------------------------------------------
# 10) REGISTER Endpoint
# ------------------------------------------------------
@app.route("/register", methods=["POST"])
def register_face():
    data = request.json
    name = data.get("name")
    sid = data.get("student_id")
    img = data.get("image")

    if not name or not sid or not img:
        return jsonify({"message":"Missing name, student_id, or image"}),400

    # decode image
    b64 = img.split(",")[1]
    raw_bytes= base64.b64decode(b64)

    ext_id = f"{name}_{sid}".replace(" ","_")
    res= rekognition_client.index_faces(
        CollectionId=COLLECTION_ID,
        Image={'Bytes':raw_bytes},
        ExternalImageId=ext_id,
        DetectionAttributes=['ALL'],
        QualityFilter='AUTO'
    )
    if not res.get('FaceRecords'):
        return jsonify({"message":"No face detected in the image"}),400

    return jsonify({"message":f"Student {name} with ID {sid} registered successfully!"}),200

# ------------------------------------------------------
# 11) RECOGNIZE Endpoint
# ------------------------------------------------------
@app.route("/recognize", methods=["POST"])
def recognize_face():
    data = request.json
    img = data.get("image")
    subject_id= data.get("subject_id") or ""
    if not img:
        return jsonify({"message":"No image provided"}),400

    # decode
    b64= img.split(",")[1]
    raw_bytes= base64.b64decode(b64)

    # Optionally do super-resolution, denoise, eq
    raw_bytes= upscale_image(raw_bytes)
    raw_bytes= denoise_image(raw_bytes)
    raw_bytes= equalize_image(raw_bytes)

    pil_img = Image.open(io.BytesIO(raw_bytes))
    regs= split_image(pil_img,grid_size=3)

    identified_people=[]
    face_count=0

    # (Optional) fetch subject_name from Firestore if you want to log
    subject_name= ""
    if subject_id:
        doc= db.collection("subjects").document(subject_id).get()
        if doc.exists:
            subject_name= doc.to_dict().get("name","")
        else:
            subject_name= "Unknown Subject"

    for region in regs:
        r_buf= io.BytesIO()
        region.save(r_buf, format="JPEG")
        region_bytes= r_buf.getvalue()

        detect= rekognition_client.detect_faces(
            Image={'Bytes':region_bytes}, Attributes=['ALL']
        )
        fds= detect.get('FaceDetails',[])
        face_count+= len(fds)

        for face in fds:
            bbox= face['BoundingBox']
            w,h= region.size
            left= int(bbox['Left']*w)
            top= int(bbox['Top']*h)
            right= int((bbox['Left']+bbox['Width'])*w)
            bottom= int((bbox['Top']+bbox['Height'])*h)
            cropped= region.crop((left,top,right,bottom))
            cbuf= io.BytesIO()
            cropped.save(cbuf,format="JPEG")
            cropped_bytes= cbuf.getvalue()

            srch= rekognition_client.search_faces_by_image(
                CollectionId=COLLECTION_ID,
                Image={'Bytes':cropped_bytes},
                MaxFaces=1,
                FaceMatchThreshold=60
            )
            fm= srch.get('FaceMatches',[])
            if not fm:
                identified_people.append({"message":"Face not recognized","confidence":"N/A"})
                continue

            match= fm[0]
            extid= match['Face']['ExternalImageId']
            conf= match['Face']['Confidence']

            parts= extid.split("_",1)
            if len(parts)==2:
                rec_name, rec_id= parts
            else:
                rec_name, rec_id= extid,"Unknown"

            identified_people.append({
                "name":rec_name,"student_id":rec_id,"confidence":conf
            })

            # Optionally log attendance
            if rec_id != "Unknown":
                record= {
                    "student_id":rec_id,
                    "name":rec_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "subject_id":subject_id,
                    "subject_name":subject_name,
                    "status":"PRESENT"
                }
                db.collection("attendance").add(record)

    return jsonify({
      "message":f"{face_count} face(s) detected in the photo.",
      "total_faces":face_count,
      "identified_people":identified_people
    }),200

# ------------------------------------------------------
# 12) SUBJECTS
# ------------------------------------------------------
@app.route("/add_subject", methods=["POST"])
def add_subject():
    data= request.json
    sname= data.get("subject_name")
    if not sname:
        return jsonify({"error":"No subject_name provided"}),400

    ref= db.collection("subjects").document()
    ref.set({"name": sname.strip(), "created_at":datetime.utcnow().isoformat()})
    return jsonify({"message": f"Subject '{sname}' added successfully!"}),200

@app.route("/get_subjects", methods=["GET"])
def get_subjects():
    docs= db.collection("subjects").stream()
    subj= []
    for d in docs:
        dd= d.to_dict()
        subj.append({"id":d.id,"name":dd.get("name","")})
    return jsonify({"subjects":subj}),200

# ------------------------------------------------------
# 13) ATTENDANCE
# ------------------------------------------------------
import openpyxl
from openpyxl import Workbook

@app.route("/api/attendance", methods=["GET"])
def get_attendance():
    sid= request.args.get("student_id")
    sbj= request.args.get("subject_id")
    start= request.args.get("start_date")
    end= request.args.get("end_date")

    ref= db.collection("attendance")
    if sid:
        ref= ref.where("student_id","==",sid)
    if sbj:
        ref= ref.where("subject_id","==",sbj)
    if start:
        dt_s= datetime.strptime(start,"%Y-%m-%d")
        ref= ref.where("timestamp",">=",dt_s.isoformat())
    if end:
        dt_e= datetime.strptime(end,"%Y-%m-%d").replace(hour=23,minute=59,second=59,microsecond=999999)
        ref= ref.where("timestamp","<=",dt_e.isoformat())

    docs= ref.stream()
    arr=[]
    for d in docs:
        dd= d.to_dict()
        dd["doc_id"]= d.id
        arr.append(dd)
    return jsonify(arr)

@app.route("/api/attendance/update", methods=["POST"])
def update_attendance():
    data= request.json
    recs= data.get("records",[])
    for r in recs:
        doc_id= r.get("doc_id")
        if not doc_id:
            continue
        ref= db.collection("attendance").document(doc_id)
        ref.update({
          "student_id":r.get("student_id",""),
          "name":r.get("name",""),
          "subject_id":r.get("subject_id",""),
          "subject_name":r.get("subject_name",""),
          "timestamp":r.get("timestamp",""),
          "status":r.get("status","")
        })
    return jsonify({"message":"Attendance records updated successfully."})

@app.route("/api/attendance/download", methods=["GET"])
def download_attendance():
    sid= request.args.get("student_id")
    sbj= request.args.get("subject_id")
    start= request.args.get("start_date")
    end= request.args.get("end_date")

    ref= db.collection("attendance")
    if sid:
        ref= ref.where("student_id","==",sid)
    if sbj:
        ref= ref.where("subject_id","==",sbj)
    if start:
        ds= datetime.strptime(start,"%Y-%m-%d")
        ref= ref.where("timestamp",">=", ds.isoformat())
    if end:
        de= datetime.strptime(end,"%Y-%m-%d").replace(hour=23,minute=59,second=59,microsecond=999999)
        ref= ref.where("timestamp","<=", de.isoformat())

    docs= ref.stream()
    arr=[]
    for d in docs:
        dd= d.to_dict()
        dd["doc_id"]= d.id
        arr.append(dd)

    wb= Workbook()
    ws= wb.active
    ws.title= "Attendance"
    headers= ["doc_id","student_id","name","subject_id","subject_name","timestamp","status"]
    ws.append(headers)

    for rec in arr:
        row= [
          rec.get("doc_id",""),
          rec.get("student_id",""),
          rec.get("name",""),
          rec.get("subject_id",""),
          rec.get("subject_name",""),
          rec.get("timestamp",""),
          rec.get("status","")
        ]
        ws.append(row)

    out= io.BytesIO()
    wb.save(out)
    out.seek(0)
    return send_file(
      out,
      mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      as_attachment=True,
      download_name="attendance.xlsx"
    )

@app.route("/api/attendance/template", methods=["GET"])
def download_template():
    wb= Workbook()
    ws= wb.active
    ws.title="Attendance Template"
    headers= ["doc_id","student_id","name","subject_id","subject_name","timestamp","status"]
    ws.append(headers)

    out= io.BytesIO()
    wb.save(out)
    out.seek(0)
    return send_file(
      out,
      mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      as_attachment=True,
      download_name="attendance_template.xlsx"
    )

@app.route("/api/attendance/upload", methods=["POST"])
def upload_attendance():
    if "file" not in request.files:
        return jsonify({"error":"No file uploaded"}),400
    file= request.files["file"]
    if not file.filename.endswith(".xlsx"):
        return jsonify({"error":"Please upload a .xlsx file"}),400

    wb= openpyxl.load_workbook(file)
    ws= wb.active
    rows= list(ws.iter_rows(values_only=True))
    expected= ("doc_id","student_id","name","subject_id","subject_name","timestamp","status")
    if not rows or rows[0]!= expected:
        return jsonify({"error":"Incorrect template format"}),400

    for row in rows[1:]:
        doc_id, student_id, name, subject_id, subject_name, timestamp, status= row
        if doc_id:
            dd= {
              "student_id": student_id or "",
              "name": name or "",
              "subject_id": subject_id or "",
              "subject_name": subject_name or "",
              "timestamp": timestamp or "",
              "status": status or ""
            }
            db.collection("attendance").document(doc_id).set(dd, merge=True)
        else:
            new_dd= {
              "student_id": student_id or "",
              "name": name or "",
              "subject_id": subject_id or "",
              "subject_name": subject_name or "",
              "timestamp": timestamp or "",
              "status": status or ""
            }
            db.collection("attendance").add(new_dd)

    return jsonify({"message":"Excel data imported successfully."})

# ------------------------------------------------------
# 14) RUN FLASK
# ------------------------------------------------------
if __name__=="__main__":
    port= int(os.getenv("PORT",5000))
    app.run(host="0.0.0.0",port=port,debug=True)
