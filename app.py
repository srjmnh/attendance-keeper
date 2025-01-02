import os
import base64
import json
import io
from datetime import datetime

from flask import Flask, request, jsonify, render_template_string, send_file
import boto3
import firebase_admin
from firebase_admin import credentials, firestore

# For face enhancements, optionally
import cv2
import numpy as np
from PIL import Image

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

def create_collection_if_not_exists():
    try:
        rekognition_client.create_collection(CollectionId=COLLECTION_ID)
        print(f"Collection '{COLLECTION_ID}' created.")
    except rekognition_client.exceptions.ResourceAlreadyExistsException:
        print(f"Collection '{COLLECTION_ID}' already exists.")

create_collection_if_not_exists()

# -----------------------------
# 2) Firebase Setup
# -----------------------------
base64_cred_str = os.getenv("FIREBASE_ADMIN_CREDENTIALS_BASE64")
if not base64_cred_str:
    raise ValueError("FIREBASE_ADMIN_CREDENTIALS_BASE64 not found in environment.")

decoded_cred = base64.b64decode(base64_cred_str)
cred_dict = json.loads(decoded_cred)
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)
db = firestore.client()

# -----------------------------
# 3) Gemini Setup
# -----------------------------
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-1.5-flash")  # or "models/chat-bison-001"

# In-memory chat memory
MAX_MEMORY = 20
conversation_memory = []

# A "system" prompt that instructs Gemini how to respond
system_prompt = """You are Gemini, an AI assistant that can:
1) Talk casually with the user.
2) If the user's prompt is about analyzing attendance (lowest, highest, or queries by subject), parse it into:
   {"action":"analytics","subject":"...","metric":"lowest_attendance"} or similar.
3) Then the system will run a Firestore query, show the result in the chat.
4) If it's not an analytics request, just respond casually.
Keep answers short and helpful.
"""

conversation_memory.append({"role":"system", "content": system_prompt})

# -----------------------------
# 4) Minimal Enhancements (Optional)
# -----------------------------
def upscale_image(image_bytes, factor=2):
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    up_img = cv2.resize(img, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
    _, up_bytes = cv2.imencode('.jpg', up_img)
    return up_bytes.tobytes()

def denoise_image(image_bytes):
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    denoised = cv2.fastNlMeansDenoisingColored(img, None, 10,10,7,21)
    _, out_bytes = cv2.imencode('.jpg', denoised)
    return out_bytes.tobytes()

def equalize_image(image_bytes):
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l,a,b = cv2.split(lab)
    l = cv2.equalizeHist(l)
    eq_lab = cv2.merge((l,a,b))
    eq_img = cv2.cvtColor(eq_lab, cv2.COLOR_LAB2BGR)
    _, eq_bytes = cv2.imencode('.jpg', eq_img)
    return eq_bytes.tobytes()

def split_image(pil_img, grid=3):
    w,h = pil_img.size
    rw, rh = w//grid, h//grid
    regs = []
    for r in range(grid):
        for c in range(grid):
            left = c*rw
            top = r*rh
            right= (c+1)*rw
            bottom=(r+1)*rh
            regs.append(pil_img.crop((left,top,right,bottom)))
    return regs

# -----------------------------
# 5) Single-Page UI (4 tabs: Register, Recognize, Subjects, Attendance),
#    plus a floating chatbot that also can do "analytics" if it detects an "action".
# -----------------------------
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Facial Recognition + Gemini Chat</title>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" />
  <link rel="stylesheet" href="https://cdn.datatables.net/1.13.4/css/jquery.dataTables.min.css" />
  <style>
    body { margin: 20px; }
    .nav-tabs .nav-link.active { font-weight: bold; }
    #attendanceTable td[contenteditable="true"] { background-color: #fcf8e3; }

    /* Chatbot */
    #chatbotToggle {
      position: fixed; bottom: 20px; right: 20px; z-index: 999;
      background-color: #0d6efd; color: #fff; border: none; border-radius: 50%;
      width: 50px; height: 50px; font-size: 22px; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
    }
    #chatbotWindow {
      position: fixed; bottom: 80px; right: 20px; width: 300px; max-height: 400px;
      border: 1px solid #ccc; border-radius: 10px; background-color: #fff;
      box-shadow: 0 0 10px rgba(0,0,0,0.2); display: none; flex-direction: column; z-index: 1000;
    }
    #chatHeader {
      background-color: #0d6efd; color: #fff; padding: 10px;
      border-radius: 10px 10px 0 0; font-weight: bold;
      display: flex; justify-content: space-between; align-items: center;
    }
    #chatHeader .close-btn { background: none; border: none; color: #fff; cursor: pointer; font-weight: bold; font-size:16px; }
    #chatMessages { flex:1; overflow-y:auto; padding:10px; font-size:14px; }
    .message { margin-bottom:10px; }
    .message.user { text-align:right; }
    .message.assistant { text-align:left; color:#333; }
    #chatInputArea { display:flex; border-top:1px solid #ddd; }
    #chatInput { flex:1; padding:8px; border:none; outline:none; font-size:14px; }
    #chatSendBtn { background-color:#0d6efd; color:#fff; border:none; padding:0 15px; cursor:pointer; }
  </style>
</head>
<body class="container">

<h1>Facial Recognition Attendance + Gemini Chat</h1>

<ul class="nav nav-tabs">
  <li class="nav-item">
    <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#registerTab">Register</button>
  </li>
  <li class="nav-item">
    <button class="nav-link" data-bs-toggle="tab" data-bs-target="#recognizeTab">Recognize</button>
  </li>
  <li class="nav-item">
    <button class="nav-link" data-bs-toggle="tab" data-bs-target="#subjectsTab">Subjects</button>
  </li>
  <li class="nav-item">
    <button class="nav-link" data-bs-toggle="tab" data-bs-target="#attendanceTab">Attendance</button>
  </li>
</ul>

<div class="tab-content mt-3">
  <!-- Register -->
  <div class="tab-pane fade show active" id="registerTab">
    <h3>Register a Face</h3>
    <label>Name</label>
    <input type="text" id="reg_name" class="form-control" placeholder="Enter name"/>
    <label>Student ID</label>
    <input type="text" id="reg_student_id" class="form-control" placeholder="Enter ID"/>
    <label>Image</label>
    <input type="file" id="reg_image" class="form-control" accept="image/*"/>
    <button onclick="registerFace()" class="btn btn-primary mt-2">Register</button>
    <div id="register_result" class="alert alert-info mt-2" style="display:none;"></div>
  </div>

  <!-- Recognize -->
  <div class="tab-pane fade" id="recognizeTab">
    <h3>Recognize a Face</h3>
    <label>Subject (optional)</label>
    <select id="rec_subject_select" class="form-control mb-2">
      <option value="">-- No Subject --</option>
    </select>
    <label>Image</label>
    <input type="file" id="rec_image" class="form-control" accept="image/*"/>
    <button onclick="recognizeFace()" class="btn btn-success mt-2">Recognize</button>
    <div id="recognize_result" class="alert alert-info mt-2" style="display:none;"></div>
  </div>

  <!-- Subjects -->
  <div class="tab-pane fade" id="subjectsTab">
    <h3>Manage Subjects</h3>
    <label>New Subject Name:</label>
    <input type="text" id="subject_name" class="form-control" placeholder="e.g. Mathematics"/>
    <button onclick="addSubject()" class="btn btn-primary mt-2">Add Subject</button>
    <div id="subject_result" class="alert alert-info mt-2" style="display:none;"></div>
    <hr/>
    <h5>Existing Subjects</h5>
    <ul id="subjects_list"></ul>
  </div>

  <!-- Attendance -->
  <div class="tab-pane fade" id="attendanceTab">
    <h3>Attendance Records</h3>
    <div class="row mb-2">
      <div class="col-md-3">
        <label>Student ID</label>
        <input type="text" id="filter_student_id" class="form-control" placeholder="e.g. 1234"/>
      </div>
      <div class="col-md-3">
        <label>Subject ID</label>
        <input type="text" id="filter_subject_id" class="form-control" placeholder="e.g. math101"/>
      </div>
      <div class="col-md-3">
        <label>Start Date</label>
        <input type="date" id="filter_start" class="form-control"/>
      </div>
      <div class="col-md-3">
        <label>End Date</label>
        <input type="date" id="filter_end" class="form-control"/>
      </div>
    </div>
    <button onclick="loadAttendance()" class="btn btn-info mb-3">Apply Filters</button>
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
      <button onclick="saveEdits()" class="btn btn-warning">Save Changes</button>
      <button onclick="downloadExcel()" class="btn btn-secondary">Download Excel</button>
      <button onclick="downloadTemplate()" class="btn btn-link">Download Template</button>
      <label class="d-block mt-3">Upload Excel:</label>
      <input type="file" id="excelFile" accept=".xlsx" class="form-control mb-2"/>
      <button onclick="uploadExcel()" class="btn btn-dark">Upload Excel</button>
    </div>
  </div>
</div>

<!-- Chatbot Toggle -->
<button id="chatbotToggle">💬</button>

<!-- Chat Window -->
<div id="chatbotWindow">
  <div id="chatHeader">
    <span>Gemini Chat</span>
    <button class="close-btn" id="chatCloseBtn">X</button>
  </div>
  <div id="chatMessages"></div>
  <div id="chatInputArea">
    <input type="text" id="chatInput" placeholder="Ask or chat..." />
    <button id="chatSendBtn">Send</button>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
<script>
  // Chat
  const toggleBtn = document.getElementById('chatbotToggle');
  const chatWindow = document.getElementById('chatbotWindow');
  const closeBtn = document.getElementById('chatCloseBtn');
  const chatMessages = document.getElementById('chatMessages');
  const chatInput = document.getElementById('chatInput');
  const chatSendBtn = document.getElementById('chatSendBtn');

  toggleBtn.addEventListener('click', () => {
    if (chatWindow.style.display === '' || chatWindow.style.display === 'none') {
      chatWindow.style.display = 'flex';
    } else {
      chatWindow.style.display = 'none';
    }
  });
  closeBtn.addEventListener('click', () => {
    chatWindow.style.display = 'none';
  });

  function addChatMessage(text, sender) {
    const div = document.createElement('div');
    div.classList.add('message', sender);
    div.textContent = text;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function sendChat() {
    const userMsg = chatInput.value.trim();
    if (!userMsg) return;
    addChatMessage(userMsg, 'user');
    chatInput.value = '';

    fetch('/process_prompt', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ prompt: userMsg })
    })
    .then(r=>r.json())
    .then(d=>{
      if (d.error) {
        addChatMessage("Error: "+d.error, 'assistant');
      } else {
        addChatMessage(d.message, 'assistant');
      }
    })
    .catch(err=>{
      addChatMessage("Network or server error!", 'assistant');
      console.error(err);
    });
  }

  chatSendBtn.addEventListener('click', sendChat);
  chatInput.addEventListener('keydown', e=>{
    if(e.key==='Enter'){
      e.preventDefault();
      sendChat();
    }
  });

  // Register
  function getBase64(file, cb){
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload=()=>cb(reader.result);
    reader.onerror=(err)=>console.error('FileReader error',err);
  }

  function registerFace(){
    const name=document.getElementById('reg_name').value.trim();
    const studentId=document.getElementById('reg_student_id').value.trim();
    const file=document.getElementById('reg_image').files[0];
    if(!name||!studentId||!file){alert('Please provide name, ID, image.');return;}
    getBase64(file,(b64)=>{
      fetch('/register',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({name, student_id:studentId, image:b64})
      })
      .then(r=>r.json())
      .then(d=>{
        const div=document.getElementById('register_result');
        div.style.display='block';
        div.textContent=d.message||d.error||JSON.stringify(d);
      })
      .catch(err=>console.error(err));
    });
  }

  // Recognize
  function recognizeFace(){
    const file=document.getElementById('rec_image').files[0];
    const subjectId=document.getElementById('rec_subject_select').value;
    if(!file){alert('No image?');return;}
    getBase64(file,(b64)=>{
      fetch('/recognize',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({image:b64, subject_id:subjectId})
      })
      .then(r=>r.json())
      .then(d=>{
        const div=document.getElementById('recognize_result');
        div.style.display='block';
        let t=d.message||d.error||JSON.stringify(d);
        if(d.identified_people){
          t+="\\n\\nIdentified People:\\n";
          d.identified_people.forEach(p=>{
            t+=`- ${p.name} (ID: ${p.student_id}), Confidence:${p.confidence}\\n`;
          });
        }
        div.textContent=t;
      })
      .catch(err=>console.error(err));
    });
  }

  // Subjects
  function addSubject(){
    const subjectName=document.getElementById('subject_name').value.trim();
    if(!subjectName){alert('No subject name?');return;}
    fetch('/add_subject',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({subject_name:subjectName})
    })
    .then(r=>r.json())
    .then(d=>{
      const div=document.getElementById('subject_result');
      div.style.display='block';
      div.textContent=d.message||d.error||JSON.stringify(d);
      document.getElementById('subject_name').value='';
      loadSubjects();
    })
    .catch(err=>console.error(err));
  }

  function loadSubjects(){
    fetch('/get_subjects')
    .then(r=>r.json())
    .then(d=>{
      const sel=document.getElementById('rec_subject_select');
      sel.innerHTML='<option value="">-- No Subject --</option>';
      (d.subjects||[]).forEach(s=>{
        const opt=document.createElement('option');
        opt.value=s.id;
        opt.textContent=s.name;
        sel.appendChild(opt);
      });
      const list=document.getElementById('subjects_list');
      if(list){ // if we exist
        list.innerHTML='';
        (d.subjects||[]).forEach(s=>{
          const li=document.createElement('li');
          li.textContent=`ID: ${s.id}, Name: ${s.name}`;
          list.appendChild(li);
        });
      }
    })
    .catch(err=>console.error(err));
  }

  // Attendance
  let attendanceTable;
  function loadAttendance(){
    const stid=document.getElementById('filter_student_id').value.trim();
    const subj=document.getElementById('filter_subject_id').value.trim();
    const start=document.getElementById('filter_start').value;
    const end=document.getElementById('filter_end').value;
    let url='/api/attendance?';
    if(stid)url+='student_id='+stid+'&';
    if(subj)url+='subject_id='+subj+'&';
    if(start)url+='start_date='+start+'&';
    if(end)url+='end_date='+end+'&';
    fetch(url)
    .then(r=>r.json())
    .then(data=>{
      if(attendanceTable){
        attendanceTable.destroy();
      }
      const tb=document.querySelector('#attendanceTable tbody');
      tb.innerHTML='';
      data.forEach(rec=>{
        const tr=document.createElement('tr');
        tr.innerHTML=`
          <td>${rec.doc_id||''}</td>
          <td contenteditable="true">${rec.student_id||''}</td>
          <td contenteditable="true">${rec.name||''}</td>
          <td contenteditable="true">${rec.subject_id||''}</td>
          <td contenteditable="true">${rec.subject_name||''}</td>
          <td contenteditable="true">${rec.timestamp||''}</td>
          <td contenteditable="true">${rec.status||''}</td>
        `;
        tb.appendChild(tr);
      });
      attendanceTable=$('#attendanceTable').DataTable({
        paging:true, searching:false, info:false, responsive:true
      });
    })
    .catch(err=>console.error(err));
  }

  function saveEdits(){
    const rows=document.querySelectorAll('#attendanceTable tbody tr');
    const updates=[];
    rows.forEach(r=>{
      const cells=r.querySelectorAll('td');
      const doc_id=cells[0].textContent.trim();
      const student_id=cells[1].textContent.trim();
      const name=cells[2].textContent.trim();
      const subject_id=cells[3].textContent.trim();
      const subject_name=cells[4].textContent.trim();
      const timestamp=cells[5].textContent.trim();
      const status=cells[6].textContent.trim();
      updates.push({doc_id, student_id,name, subject_id,subject_name,timestamp,status});
    });
    fetch('/api/attendance/update',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({records:updates})
    })
    .then(r=>r.json())
    .then(d=>alert(d.message||JSON.stringify(d)))
    .catch(err=>console.error(err));
  }

  function downloadExcel(){
    const stid=document.getElementById('filter_student_id').value.trim();
    const subj=document.getElementById('filter_subject_id').value.trim();
    const start=document.getElementById('filter_start').value;
    const end=document.getElementById('filter_end').value;
    let url='/api/attendance/download?';
    if(stid)url+='student_id='+stid+'&';
    if(subj)url+='subject_id='+subj+'&';
    if(start)url+='start_date='+start+'&';
    if(end)url+='end_date='+end+'&';
    window.location.href=url;
  }

  function downloadTemplate(){
    window.location.href='/api/attendance/template';
  }

  function uploadExcel(){
    const f=document.getElementById('excelFile').files[0];
    if(!f){alert('No file?');return;}
    const fd=new FormData();
    fd.append('file',f);
    fetch('/api/attendance/upload',{
      method:'POST', body:fd
    })
    .then(r=>r.json())
    .then(d=>{
      alert(d.message||d.error||'Excel uploaded');
      loadAttendance();
    })
    .catch(err=>console.error(err));
  }

  document.addEventListener('DOMContentLoaded',loadSubjects);
</script>
</body>
</html>
"""

app = Flask(__name__)

@app.route("/")
def index():
    # Render our big single-page
    return render_template_string(INDEX_HTML)

# -----------------------------
# Register
# -----------------------------
@app.route("/register", methods=["POST"])
def register_face():
    data = request.json
    name = data.get("name")
    student_id = data.get("student_id")
    image = data.get("image")
    if not name or not student_id or not image:
        return jsonify({"message":"Missing name,student_id,image"}),400

    sanitized_name = "".join(c if c.isalnum() or c in "_-." else "_" for c in name)
    image_data = image.split(",")[1]
    image_bytes = base64.b64decode(image_data)

    external_image_id = f"{sanitized_name}_{student_id}"
    resp = rekognition_client.index_faces(
        CollectionId=COLLECTION_ID,
        Image={'Bytes':image_bytes},
        ExternalImageId=external_image_id,
        DetectionAttributes=['ALL'],
        QualityFilter='AUTO'
    )
    if not resp.get('FaceRecords'):
        return jsonify({"message":"No face detected"}),400
    return jsonify({"message":f"Student {name} with ID {student_id} registered!"}),200

# -----------------------------
# Recognize
# -----------------------------
@app.route("/recognize", methods=["POST"])
def recognize():
    data = request.json
    image_str = data.get("image")
    subject_id = data.get("subject_id") or ""
    if not image_str:
        return jsonify({"message":"No image provided"}),400

    # optional subject name
    subject_name=""
    if subject_id:
        doc=db.collection("subjects").document(subject_id).get()
        if doc.exists:
            subject_name = doc.to_dict().get("name","Unknown Subject")

    raw_b64 = image_str.split(",")[1]
    raw_bytes=base64.b64decode(raw_b64)
    # optional enhancements
    raw_bytes=upscale_image(raw_bytes)
    raw_bytes=denoise_image(raw_bytes)
    raw_bytes=equalize_image(raw_bytes)

    pil_img=Image.open(io.BytesIO(raw_bytes))

    # split
    def split_image(pil_img,grid=3):
        w,h=pil_img.size
        rw, rh = w//grid, h//grid
        regs=[]
        for r in range(grid):
            for c in range(grid):
                left=c*rw
                top=r*rh
                right=(c+1)*rw
                bottom=(r+1)*rh
                regs.append(pil_img.crop((left,top,right,bottom)))
        return regs

    regions=split_image(pil_img,3)

    identified_people=[]
    face_count=0
    for region in regions:
        buf=io.BytesIO()
        region.save(buf,format="JPEG")
        region_bytes=buf.getvalue()

        det=rekognition_client.detect_faces(
            Image={'Bytes':region_bytes}, Attributes=['ALL']
        )
        faces=det.get('FaceDetails',[])
        face_count+=len(faces)
        for f in faces:
            bbox=f['BoundingBox']
            w,h=region.size
            left=int(bbox['Left']*w)
            top=int(bbox['Top']*h)
            rght=int((bbox['Left']+bbox['Width'])*w)
            bot=int((bbox['Top']+bbox['Height'])*h)
            cf=region.crop((left,top,rght,bot))
            cbuf=io.BytesIO()
            cf.save(cbuf,format="JPEG")
            cfac=cbuf.getvalue()
            sr=rekognition_client.search_faces_by_image(
                CollectionId=COLLECTION_ID,
                Image={'Bytes':cfac},
                MaxFaces=1,
                FaceMatchThreshold=60
            )
            matches=sr.get('FaceMatches',[])
            if not matches:
                identified_people.append({"message":"Face not recognized","confidence":"N/A"})
                continue
            m=matches[0]
            ext_id=m['Face']['ExternalImageId']
            conf=m['Face']['Confidence']
            parts=ext_id.split("_",1)
            if len(parts)==2:
                rec_name, rec_id=parts
            else:
                rec_name, rec_id=ext_id,"Unknown"

            identified_people.append({"name":rec_name,"student_id":rec_id,"confidence":conf})

            # log attendance
            if rec_id!="Unknown":
                doc={
                  "student_id":rec_id,
                  "name":rec_name,
                  "timestamp":datetime.utcnow().isoformat(),
                  "subject_id":subject_id,
                  "subject_name":subject_name,
                  "status":"PRESENT"
                }
                db.collection("attendance").add(doc)

    return jsonify({
      "message":f"{face_count} face(s) detected in the photo.",
      "total_faces":face_count,
      "identified_people":identified_people
    }),200

# -----------------------------
# Subjects
# -----------------------------
@app.route("/add_subject", methods=["POST"])
def add_subject():
    d=request.json
    subject_name=d.get("subject_name")
    if not subject_name:
        return jsonify({"error":"No subject_name"}),400
    doc_ref=db.collection("subjects").document()
    doc_ref.set({"name":subject_name.strip(),"created_at":datetime.utcnow().isoformat()})
    return jsonify({"message":f"Subject '{subject_name}' added."}),200

@app.route("/get_subjects", methods=["GET"])
def get_subjects():
    subs=db.collection("subjects").stream()
    subjects_list=[]
    for s in subs:
        dd=s.to_dict()
        subjects_list.append({"id":s.id,"name":dd.get("name","")})
    return jsonify({"subjects":subjects_list}),200

# -----------------------------
# Attendance
# -----------------------------
import openpyxl
from openpyxl import Workbook

@app.route("/api/attendance", methods=["GET"])
def list_attendance():
    stid=request.args.get("student_id")
    subid=request.args.get("subject_id")
    start=request.args.get("start_date")
    end=request.args.get("end_date")
    q=db.collection("attendance")
    if stid:
        q=q.where("student_id","==",stid)
    if subid:
        q=q.where("subject_id","==",subid)
    if start:
        dt_start=datetime.strptime(start,"%Y-%m-%d")
        q=q.where("timestamp",">=",dt_start.isoformat())
    if end:
        dt_end=datetime.strptime(end,"%Y-%m-%d").replace(hour=23,minute=59,second=59,microsecond=999999)
        q=q.where("timestamp","<=",dt_end.isoformat())

    docs=q.stream()
    output=[]
    for doc_ in docs:
        d=doc_.to_dict()
        d["doc_id"]=doc_.id
        output.append(d)
    return jsonify(output)

@app.route("/api/attendance/update", methods=["POST"])
def update_attendance():
    data=request.json
    recs=data.get("records",[])
    for r in recs:
        doc_id=r.get("doc_id")
        if not doc_id: continue
        ref=db.collection("attendance").document(doc_id)
        dd={
          "student_id": r.get("student_id",""),
          "name": r.get("name",""),
          "subject_id": r.get("subject_id",""),
          "subject_name": r.get("subject_name",""),
          "timestamp": r.get("timestamp",""),
          "status": r.get("status",""),
        }
        ref.update(dd)
    return jsonify({"message":"Attendance records updated."})

@app.route("/api/attendance/download", methods=["GET"])
def download_attendance():
    stid=request.args.get("student_id")
    subid=request.args.get("subject_id")
    start=request.args.get("start_date")
    end=request.args.get("end_date")
    q=db.collection("attendance")
    if stid:
        q=q.where("student_id","==",stid)
    if subid:
        q=q.where("subject_id","==",subid)
    if start:
        dt_start=datetime.strptime(start,"%Y-%m-%d")
        q=q.where("timestamp",">=",dt_start.isoformat())
    if end:
        dt_end=datetime.strptime(end,"%Y-%m-%d").replace(hour=23,minute=59,second=59,microsecond=999999)
        q=q.where("timestamp","<=",dt_end.isoformat())

    docs=q.stream()
    recs=[]
    for d in docs:
        dd=d.to_dict()
        dd["doc_id"]=d.id
        recs.append(dd)
    wb=Workbook()
    ws=wb.active
    ws.title="Attendance"
    headers=["doc_id","student_id","name","subject_id","subject_name","timestamp","status"]
    ws.append(headers)
    for r in recs:
        row=[
          r.get("doc_id",""),
          r.get("student_id",""),
          r.get("name",""),
          r.get("subject_id",""),
          r.get("subject_name",""),
          r.get("timestamp",""),
          r.get("status","")
        ]
        ws.append(row)
    out=io.BytesIO()
    wb.save(out)
    out.seek(0)
    return send_file(
      out,
      mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      as_attachment=True,
      download_name="attendance.xlsx"
    )

@app.route("/api/attendance/template", methods=["GET"])
def template():
    wb=Workbook()
    ws=wb.active
    ws.title="AttendanceTemplate"
    h=["doc_id","student_id","name","subject_id","subject_name","timestamp","status"]
    ws.append(h)
    out=io.BytesIO()
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
        return jsonify({"error":"No file"}),400
    f=request.files["file"]
    if not f.filename.endswith(".xlsx"):
        return jsonify({"error":"Please upload .xlsx"}),400

    import openpyxl
    wb=openpyxl.load_workbook(f)
    ws=wb.active
    rows=list(ws.iter_rows(values_only=True))
    expected=("doc_id","student_id","name","subject_id","subject_name","timestamp","status")
    if not rows or rows[0]!=expected:
        return jsonify({"error":"Incorrect template format"}),400

    for row in rows[1:]:
        doc_id, stid, nm, subid, subnm, ts, status=row
        if doc_id:
            dd={
              "student_id": stid or "",
              "name": nm or "",
              "subject_id": subid or "",
              "subject_name": subnm or "",
              "timestamp": ts or "",
              "status": status or ""
            }
            db.collection("attendance").document(doc_id).set(dd,merge=True)
        else:
            newd={
              "student_id": stid or "",
              "name": nm or "",
              "subject_id": subid or "",
              "subject_name": subnm or "",
              "timestamp": ts or "",
              "status": status or ""
            }
            db.collection("attendance").add(newd)
    return jsonify({"message":"Excel data imported successfully."})

# -----------------------------
# 6) /process_prompt => interpret user chat. If analytics, do Firestore query, else respond
# -----------------------------
@app.route("/process_prompt", methods=["POST"])
def process_prompt():
    data=request.json
    user_prompt=data.get("prompt","").strip()
    if not user_prompt:
        return jsonify({"error":"No prompt provided"}),400

    # Add user message
    conversation_memory.append({"role":"user","content":user_prompt})
    # Build conversation string
    conv_str=""
    for msg in conversation_memory:
        if msg["role"]=="system":
            conv_str+=f"System: {msg['content']}\n"
        elif msg["role"]=="user":
            conv_str+=f"User: {msg['content']}\n"
        else:
            conv_str+=f"Assistant: {msg['content']}\n"

    # Step 1: Let Gemini classify or parse
    # We'll ask it: "Decide if this is analytics or casual. If analytics, output JSON with {action:'analytics', subject:'X', metric:'lowest_attendance'}. If not, say {action:'casual'}."
    classification_prompt=conv_str+"\nYou are an advanced assistant. Output EXACT valid JSON, either {\"action\":\"casual\"} or {\"action\":\"analytics\",\"subject\":\"...\",\"metric\":\"lowest_attendance\"} for example."
    classification_resp=model.generate_content(classification_prompt)
    if not classification_resp.candidates:
        # fallback
        assistant_reply="I'm having trouble responding."
    else:
        # parse the classification
        raw=classification_resp.candidates[0].content.parts[0].text.strip()
        # attempt to decode JSON
        try:
            # e.g. {"action":"analytics","subject":"physics","metric":"lowest_attendance"}
            classification_data=json.loads(raw)
            if classification_data.get("action")=="analytics":
                # e.g. subject=classification_data["subject"], metric=lowest_attendance
                subject_str=classification_data.get("subject","")
                metric=classification_data.get("metric","lowest_attendance")
                # run a Firestore query
                # Example: "lowest attendance for subject"
                # This is naive - you'd customize your logic
                # For "lowest_attendance", we interpret as "the student with the fewest 'PRESENT' docs for that subject"
                analytics_result=run_analytics_lowest_attendance(subject_str)
                assistant_reply=f"For subject={subject_str}, lowest attendance is: {analytics_result}"
            else:
                # casual
                # Generate a normal chat reply
                normal_resp=model.generate_content(conv_str)
                if not normal_resp.candidates:
                    assistant_reply="Hmm, I'm stuck."
                else:
                    assistant_reply="".join(part.text for part in normal_resp.candidates[0].content.parts).strip()
        except:
            # fallback if JSON parse fails, treat as casual
            normal_resp=model.generate_content(conv_str)
            if not normal_resp.candidates:
                assistant_reply="Hmm, I'm stuck."
            else:
                assistant_reply="".join(part.text for part in normal_resp.candidates[0].content.parts).strip()

    # Add to memory
    conversation_memory.append({"role":"assistant","content":assistant_reply})
    # Trim
    if len(conversation_memory)>MAX_MEMORY:
        conversation_memory.pop(0)
    return jsonify({"message":assistant_reply})

def run_analytics_lowest_attendance(subject_str):
    """
    Example logic: For each student, count how many attendance docs with subject_id=subject_str.
    Return the student with the fewest.
    This is naive and not optimized. If you want 'lowest attendance rate' you need total possible days, etc.
    """
    # Gather all attendance with subject_id=subject_str
    q=db.collection("attendance").where("subject_id","==",subject_str)
    docs=q.stream()
    # count by student
    from collections import Counter
    counts=Counter()
    for d in docs:
        dd=d.to_dict()
        stid=dd.get("student_id","Unknown")
        counts[stid]+=1

    if not counts:
        return "No attendance records found for subject."
    # find min
    min_val=min(counts.values())
    # find who has that min
    # possibly multiple
    losers=[k for k,v in counts.items() if v==min_val]
    # e.g. "Student 1234 with 2"
    return f"{', '.join(losers)} with {min_val} record(s)"

# -----------------------------
# 7) Run
# -----------------------------
if __name__=="__main__":
    port=int(os.getenv("PORT","5000"))
    app.run(host="0.0.0.0",port=port,debug=True)