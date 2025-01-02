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

  // If the sender is the assistant, animate the chatbot window
  if (sender === 'assistant') {
    if (chatWindow.style.display === 'none' || chatWindow.style.display === '') {
      chatWindow.style.display = 'flex';
    }
  }
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
      // Notify Gemini about the registration
      if (data.message) {
        notifyGemini('register', `Registered new student: ${name}, ID: ${studentId}`);
      } else if (data.error) {
        notifyGemini('error', `Registration error: ${data.error}`);
      }
    })
    .catch(err => {
      console.error(err);
      const div = document.getElementById('register_result');
      div.style.display = 'block';
      div.textContent = "An error occurred during registration.";
      // Notify Gemini about the error
      notifyGemini('error', 'An error occurred during registration.');
    });
  });
}

/* Recognize Face */
function recognizeFace() {
  const file = document.getElementById('rec_image').files[0];
  const subjectId = document.getElementById('rec_subject_select').value;
  if (!file) {
    alert('Please select an image to recognize.');
    return;
  }
  getBase64(file, (base64Str) => {
    // Show progress bar
    document.getElementById('recognize_progress').style.display = 'block';
    document.querySelector('#recognize_progress .progress-bar').style.width = '0%';

    // Simulate progress
    let progress = 0;
    const progressInterval = setInterval(() => {
      if (progress >= 100) {
        clearInterval(progressInterval);
      } else {
        progress += 10;
        document.querySelector('#recognize_progress .progress-bar').style.width = `${progress}%`;
      }
    }, 300); // Update every 300ms

    fetch('/recognize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: base64Str, subject_id: subjectId })
    })
    .then(res => res.json())
    .then(data => {
      clearInterval(progressInterval);
      document.getElementById('recognize_progress').style.display = 'none';
      const div = document.getElementById('recognize_result');
      div.style.display = 'block';

      let htmlContent = `<strong>${data.message}</strong><br/>`;
      if (data.identified_people && data.identified_people.length > 0) {
        htmlContent += '<div class="row mt-3">';
        data.identified_people.forEach(person => {
          htmlContent += `
            <div class="col-md-4">
              <div class="card mb-3">
                <div class="card-body">
                  <h5 class="card-title">${person.name || "Unknown"}</h5>
                  <p class="card-text">ID: ${person.student_id || "N/A"}</p>
                  <p class="card-text">Confidence: ${person.confidence ? person.confidence.toFixed(2) : "N/A"}</p>
                </div>
              </div>
            </div>
          `;
        });
        htmlContent += '</div>';
      }
      div.innerHTML = htmlContent;

      // Notify Gemini about the recognition
      if (data.message) {
        notifyGemini('recognize', data.message);
      }
    })
    .catch(err => {
      clearInterval(progressInterval);
      document.getElementById('recognize_progress').style.display = 'none';
      const div = document.getElementById('recognize_result');
      div.style.display = 'block';
      div.textContent = "An error occurred during recognition.";

      // Notify Gemini about the error
      notifyGemini('error', 'An error occurred during recognition.');
      console.error(err);
    });
  });
}

/* Subjects */
function addSubject() {
  const subjectName = document.getElementById('subject_name').value.trim();
  if (!subjectName) {
    alert('Please enter subject name.');
    return;
  }
  fetch('/api/subjects/add', {
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

    // Notify Gemini about the action
    if (data.message) {
      notifyGemini('add_subject', `Added new subject: ${subjectName}`);
    } else if (data.error) {
      notifyGemini('error', `Add subject error: ${data.error}`);
    }
  })
  .catch(err => {
    console.error(err);
    const div = document.getElementById('subject_result');
    div.style.display = 'block';
    div.textContent = "An error occurred while adding the subject.";
    // Notify Gemini about the error
    notifyGemini('error', 'An error occurred while adding the subject.');
  });
}

function loadSubjects() {
  fetch('/api/subjects/get')
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
  .catch(err => {
    console.error(err);
    // Notify Gemini about the error
    notifyGemini('error', 'Failed to load subjects.');
  });
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
    .catch(err => {
      console.error(err);
      // Notify Gemini about the error
      notifyGemini('error', 'Failed to load attendance records.');
    });
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
    // Notify Gemini about the update
    if (resp.message) {
      notifyGemini('update_attendance', resp.message);
    }
  })
  .catch(err => {
    console.error(err);
    alert("An error occurred while saving changes.");
    // Notify Gemini about the error
    notifyGemini('error', 'Failed to save attendance changes.');
  });
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
  // Notify Gemini about the download
  notifyGemini('download_excel', 'Downloaded attendance records as Excel.');
}

function downloadTemplate() {
  window.location.href = '/api/attendance/template';
  // Notify Gemini about the template download
  notifyGemini('download_template', 'Downloaded attendance template.');
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
    // Notify Gemini about the upload
    if (resp.message) {
      notifyGemini('upload_excel', resp.message);
    } else if (resp.error) {
      notifyGemini('error', `Upload Excel error: ${resp.error}`);
    }
  })
  .catch(err => {
    console.error(err);
    alert("An error occurred while uploading Excel.");
    // Notify Gemini about the error
    notifyGemini('error', 'Failed to upload Excel.');
  });
}

document.addEventListener('DOMContentLoaded', () => {
  loadSubjects();
});

/* -------------- Chatbot Notification Function -------------- */
function notifyGemini(action, details) {
  fetch('/notify_gemini', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: action, details: details })
  })
  .then(res => res.json())
  .then(data => {
    // Optionally handle response
    if (data.message) {
      console.log("Gemini notified:", data.message);
    }
  })
  .catch(err => {
    console.error("Failed to notify Gemini:", err);
  });
}