/* -------------- SocketIO Initialization -------------- */
// Initialize SocketIO
const socket = io();

// Listen for messages from the backend
socket.on('connect', () => {
    console.log('Connected to SocketIO server');
});

socket.on('chat_message', (data) => {
    addMessage(data.message, 'assistant');
});

socket.on('disconnect', () => {
    console.log('Disconnected from SocketIO server');
});

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

// Send message on button click
chatSendBtn.addEventListener('click', sendMessage);

// Send message on Enter key
chatInput.addEventListener('keypress', (e) => {
  if (e.key === 'Enter') {
    sendMessage();
  }
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
      // The assistant's response is handled via SocketIO
      // So no need to addMessage here
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
  const subjectId = document.getElementById('rec_subject_select').value;
  if (!file) {
    alert('Please select an image to recognize.');
    return;
  }
  getBase64(file, (base64Str) => {
    // Show progress bar
    document.getElementById('recognitionProgress').style.display = 'block';
    document.getElementById('recognize_result').style.display = 'none';
    document.getElementById('identified_faces').innerHTML = '';

    fetch('/recognize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: base64Str, subject_id: subjectId })
    })
    .then(res => res.json())
    .then(data => {
      // Hide progress bar
      document.getElementById('recognitionProgress').style.display = 'none';
      const div = document.getElementById('recognize_result');
      div.style.display = 'block';
      let text = data.message || data.error || JSON.stringify(data);
      if (data.identified_people) {
        text += "\n\nIdentified People:\n";
        data.identified_people.forEach((p) => {
          text += `- ${p.name || "Unknown"} (ID: ${p.student_id || "N/A"}), Confidence: ${p.confidence}\n`;
        });
      }
      div.textContent = text;

      // Display identified faces beautifully
      if (data.identified_people && data.identified_people.length > 0) {
        const facesDiv = document.getElementById('identified_faces');
        facesDiv.innerHTML = '<h5>Identified Faces:</h5>';
        data.identified_people.forEach(person => {
          const card = document.createElement('div');
          card.classList.add('card', 'mb-2');
          card.style.width = '18rem';
          card.innerHTML = `
            <div class="card-body">
              <h5 class="card-title">${person.name || "Unknown"}</h5>
              <p class="card-text">ID: ${person.student_id || "N/A"}</p>
              <p class="card-text">Confidence: ${person.confidence || "N/A"}</p>
            </div>
          `;
          facesDiv.appendChild(card);
        });
      }
    })
    .catch(err => {
      document.getElementById('recognitionProgress').style.display = 'none';
      addMessage("Network or server error!", 'assistant');
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
  fetch('/api/subjects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: subjectName })
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
  fetch('/api/subjects')
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
  const endDate = document.getElementById('filter_end').value.trim();

  let url = '/api/attendance/get?';
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
    socket.emit('chat_message', { message: resp.message || "Attendance records updated." });
  })
  .catch(err => console.error(err));
}

function downloadExcel() {
  const studentId = document.getElementById('filter_student_id').value.trim();
  const subjectId = document.getElementById('filter_subject_id').value.trim();
  const startDate = document.getElementById('filter_start').value;
  const endDate = document.getElementById('filter_end').value.trim();

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
    socket.emit('chat_message', { message: resp.message || "Excel data uploaded." });
    loadAttendance();
  })
  .catch(err => console.error(err));
}

/* Initialize on DOM Content Loaded */
document.addEventListener('DOMContentLoaded', () => {
  loadSubjects();
});