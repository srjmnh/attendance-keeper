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

  // Show progress bar
  const progressBar = document.querySelector('.progress');
  const recognizeProgress = document.getElementById('recognizeProgress');
  progressBar.style.display = 'block';
  recognizeProgress.style.width = '0%';
  recognizeProgress.textContent = '0%';

  fetch('/process_prompt', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt: userMessage })
  })
  .then(res => res.json())
  .then(data => {
    // Hide progress bar
    progressBar.style.display = 'none';

    if (data.error) {
      addMessage("Error: " + data.error, 'assistant');
    } else {
      addMessage(data.message, 'assistant');
    }
  })
  .catch(err => {
    // Hide progress bar
    progressBar.style.display = 'none';

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
      div.className = data.message.includes("successfully") ? "alert alert-success" : "alert alert-danger";
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
    fetch('/recognize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: base64Str, subject_id: subjectId })
    })
    .then(res => res.json())
    .then(data => {
      const div = document.getElementById('recognize_result');
      div.style.display = 'block';
      div.className = "alert alert-info";
      let text = data.message || data.error || JSON.stringify(data);
      if (data.identified_people) {
        text += "\n\nIdentified People:\n";
        data.identified_people.forEach((p, index) => {
          text += `- Name: ${p.name || "Unknown"}, ID: ${p.student_id || "N/A"}, Confidence: ${p.confidence || "N/A"}%\n`;
        });
        div.textContent = text;

        // Display Recognized Faces
        displayRecognizedFaces(data.identified_people);
      } else {
        div.textContent = text;
      }
    })
    .catch(err => console.error(err));
  });
}

function displayRecognizedFaces(people) {
  const facesDiv = document.getElementById('recognizedFaces');
  facesDiv.innerHTML = ''; // Clear previous faces
  people.forEach((person, index) => {
    const faceCard = document.createElement('div');
    faceCard.classList.add('face-card');

    // Assuming you have the cropped face image stored or can be retrieved
    // For demonstration, using a placeholder image
    const img = document.createElement('img');
    img.src = 'https://via.placeholder.com/150';  // Replace with actual cropped face image URL if available
    img.alt = `Face ${index + 1}`;
    faceCard.appendChild(img);

    const infoDiv = document.createElement('div');
    infoDiv.classList.add('face-info');
    infoDiv.innerHTML = `
      <p><strong>Name:</strong> ${person.name || "Unknown"}</p>
      <p><strong>ID:</strong> ${person.student_id || "N/A"}</p>
      <p><strong>Confidence:</strong> ${person.confidence || "N/A"}%</p>
    `;
    faceCard.appendChild(infoDiv);

    facesDiv.appendChild(faceCard);
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
    div.className = data.message.includes("successfully") ? "alert alert-success" : "alert alert-danger";
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
    loadAttendance();
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
  loadSubjects();
});