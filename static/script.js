<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Facial Recognition Attendance + Gemini Chat</title>
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- DataTables CSS -->
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.4/css/jquery.dataTables.min.css">
    <!-- SocketIO Client -->
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"
            integrity="sha384-YVt05JxY1VamH9eBjQkKlg1RZbIPq5+Vc8yPyb/d/RrjF7HnDwK5a5rP0df4k6Cc"
            crossorigin="anonymous"></script>
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
          max-height: 500px;
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

        /* Progress Bar */
        .progress {
          height: 20px;
        }
        .progress-bar {
          line-height: 20px;
        }
    </style>
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
    <button onclick="recognize()" class="btn btn-success mt-2">Recognize</button>
    
    <!-- Progress Bar -->
    <div class="progress mt-3" style="display: none;" id="recognizeProgress">
        <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar"
             aria-valuenow="100" aria-valuemin="0" aria-valuemax="100" style="width: 100%"></div>
    </div>
    
    <div id="recognize_result" class="mt-3"></div>
    <div id="identified_faces" class="row mt-3"></div>
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
<script src="/static/script.js"></script>
</body>
</html>