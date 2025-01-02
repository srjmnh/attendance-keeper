// Initialize SocketIO
const socket = io();

// Listen for action_feedback events from the backend
socket.on('action_feedback', (data) => {
    const { message, type } = data;
    if (type === 'success') {
        addChatbotMessage(`✅ ${message}`);
    } else if (type === 'error') {
        addChatbotMessage(`❌ ${message}`);
    } else if (type === 'info') {
        addChatbotMessage(`ℹ️ ${message}`);
    }
});

// Chatbot Functions
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

function addChatbotMessage(text) {
    const div = document.createElement('div');
    div.classList.add('message', 'assistant');
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
        .catch(err => {
            console.error(err);
            addChatbotMessage(`❌ Error during registration: ${err}`);
        });
    });
}

/* Recognize Faces */
function recognize() {
    const file = document.getElementById('rec_image').files[0];
    const subjectId = document.getElementById('rec_subject_select').value;

    if (!file) {
        alert('Please upload an image.');
        return;
    }

    getBase64(file, (imageData) => {
        // Show progress bar
        document.getElementById('recognizeProgress').style.display = 'block';
        document.getElementById('recognize_result').innerHTML = '';
        document.getElementById('identified_faces').innerHTML = '';

        fetch('/recognize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData, subject_id: subjectId })
        })
        .then(res => res.json())
        .then(data => {
            // Hide progress bar
            document.getElementById('recognizeProgress').style.display = 'none';

            const resultDiv = document.getElementById('recognize_result');
            resultDiv.innerHTML = '';

            if (data.message) {
                const messageP = document.createElement('p');
                messageP.textContent = data.message;
                resultDiv.appendChild(messageP);
            }

            if (data.identified_people && data.identified_people.length > 0) {
                const facesDiv = document.getElementById('identified_faces');
                facesDiv.innerHTML = '<h4>Identified Faces:</h4>';

                data.identified_people.forEach((person) => {
                    // Create a Bootstrap card for each identified face
                    const card = document.createElement('div');
                    card.classList.add('col-md-4', 'mb-3');

                    card.innerHTML = `
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">${person.name || "Unknown"}</h5>
                                <p class="card-text">
                                    <strong>ID:</strong> ${person.student_id || "N/A"}<br>
                                    <strong>Confidence:</strong> ${person.confidence || "N/A"}%
                                </p>
                            </div>
                        </div>
                    `;

                    facesDiv.appendChild(card);
                });
            }
        })
        .catch(error => {
            // Hide progress bar
            document.getElementById('recognizeProgress').style.display = 'none';

            // Display error in recognize_result
            const resultDiv = document.getElementById('recognize_result');
            resultDiv.innerHTML = `<p class="text-danger">Error: ${error}</p>`;

            // Notify chatbot about the error
            addChatbotMessage(`❌ Error during recognition: ${error}`);
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
    .catch(err => {
        console.error(err);
        addChatbotMessage(`❌ Error adding subject: ${err}`);
    });
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
    .catch(err => {
        console.error(err);
        addChatbotMessage(`❌ Error loading subjects: ${err}`);
    });
}

/* Attendance */
function loadAttendance() {
    const studentId = document.getElementById('filter_student_id').value.trim();
    const subjectId = document.getElementById('filter_subject_id').value.trim();
    const startDate = document.getElementById('filter_start').value;
    const endDate = document.getElementById('filter_end').value.trim();

    let url = '/api/attendance?';
    if (studentId) url += 'student_id=' + encodeURIComponent(studentId) + '&';
    if (subjectId) url += 'subject_id=' + encodeURIComponent(subjectId) + '&';
    if (startDate) url += 'start_date=' + encodeURIComponent(startDate) + '&';
    if (endDate) url += 'end_date=' + encodeURIComponent(endDate) + '&';

    fetch(url)
      .then(res => res.json())
      .then(data => {
        attendanceData = data;
        renderAttendanceTable(attendanceData);
      })
      .catch(err => {
          console.error(err);
          addChatbotMessage(`❌ Error loading attendance records: ${err}`);
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
    })
    .catch(err => {
        console.error(err);
        addChatbotMessage(`❌ Error saving attendance records: ${err}`);
    });
}

function downloadExcel() {
    const studentId = document.getElementById('filter_student_id').value.trim();
    const subjectId = document.getElementById('filter_subject_id').value.trim();
    const startDate = document.getElementById('filter_start').value;
    const endDate = document.getElementById('filter_end').value.trim();

    let url = '/api/attendance/download?';
    if (studentId) url += 'student_id=' + encodeURIComponent(studentId) + '&';
    if (subjectId) url += 'subject_id=' + encodeURIComponent(subjectId) + '&';
    if (startDate) url += 'start_date=' + encodeURIComponent(startDate) + '&';
    if (endDate) url += 'end_date=' + encodeURIComponent(endDate) + '&';

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
    .catch(err => {
        console.error(err);
        addChatbotMessage(`❌ Error uploading Excel file: ${err}`);
    });
}

/* Initialize on DOM Content Loaded */
document.addEventListener('DOMContentLoaded', () => {
    loadSubjects();
});