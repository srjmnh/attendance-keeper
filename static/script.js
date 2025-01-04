function getBase64(file, callback) {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => callback(reader.result);
    reader.onerror = (error) => console.error('Error: ', error);
}

function registerUser() {
    const name = document.getElementById('name').value;
    const studentId = document.getElementById('student_id').value;
    const file = document.getElementById('register_image').files[0];

    if (!name || !studentId || !file) {
        alert('Please provide name, student ID, and an image.');
        return;
    }

    getBase64(file, (imageData) => {
        fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name, student_id: studentId, image: imageData }),
        })
        .then(response => response.json())
        .then(data => {
            const resultDiv = document.getElementById('register_result');
            if (data.message) {
                resultDiv.className = 'text-success mt-2';
                resultDiv.innerText = data.message;
            } else {
                resultDiv.className = 'text-danger mt-2';
                resultDiv.innerText = data.error;
            }
        })
        .catch(error => console.error('Error:', error));
    });
}

function recognizeFace() {
    const file = document.getElementById('rec_image').files[0];
    const subjectSelect = document.getElementById('rec_subject_select');
    const subject_id = subjectSelect.value;

    if (!file) {
        alert('Please upload an image.');
        return;
    }

    getBase64(file, (imageData) => {
        fetch('/recognize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ image: imageData, subject_id: subject_id }),
        })
        .then(response => response.json())
        .then(data => {
            const resultDiv = document.getElementById('recognize_result');
            if (data.error) {
                resultDiv.className = 'alert alert-danger mt-3';
                resultDiv.innerText = data.error;
            } else {
                let resultHTML = `<p>${data.message}</p>`;
                if (data.identified_people && data.identified_people.length > 0) {
                    resultHTML += `<p>Total Faces Detected: ${data.total_faces}</p><ul>`;
                    data.identified_people.forEach(person => {
                        resultHTML += `<li><strong>Face ${person.face_number}:</strong> Name: ${person.name || "Unknown"}, ID: ${person.student_id || "N/A"}, Confidence: ${person.confidence || "N/A"}%</li>`;
                    });
                    resultHTML += "</ul>";
                }
                resultDiv.className = 'alert alert-info mt-3';
                resultDiv.innerHTML = resultHTML;
                resultDiv.style.display = 'block';
            }
        })
        .catch(error => console.error('Error:', error));
    });
}

function loadSubjects() {
    fetch('/subjects')
    .then(response => response.json())
    .then(data => {
        const subjectsList = document.getElementById('subjects_list');
        subjectsList.innerHTML = '';
        data.subjects.forEach(subject => {
            const li = document.createElement('li');
            li.innerHTML = `${subject.name} 
                <button onclick="deleteSubject('${subject.id}')" class="btn btn-sm btn-danger ms-2">Delete</button>`;
            subjectsList.appendChild(li);
        });
    })
    .catch(error => console.error('Error:', error));
}

function addSubject() {
    const subjectName = document.getElementById('new_subject_name').value.trim();

    if (!subjectName) {
        alert('Please enter a subject name.');
        return;
    }

    fetch('/api/subjects', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: subjectName }),
    })
    .then(response => response.json())
    .then(data => {
        const resultDiv = document.getElementById('add_subject_result');
        if (data.message) {
            resultDiv.className = 'alert alert-success mt-2';
            resultDiv.innerText = data.message;
            document.getElementById('new_subject_name').value = '';
            // Add new row to Subjects DataTable
            subjectsTable.row.add([
                data.subject.id,
                data.subject.name,
                `<button onclick="saveSubject('${data.subject.id}')" class="btn btn-sm btn-success">Save</button>
                 <button onclick="deleteSubject('${data.subject.id}')" class="btn btn-sm btn-danger">Delete</button>`
            ]).draw(false);
        } else {
            resultDiv.className = 'alert alert-danger mt-2';
            resultDiv.innerText = data.error;
        }
        resultDiv.style.display = 'block';
    })
    .catch(error => console.error('Error:', error));
}

function saveSubject(subjectId) {
    const row = $(`tr[data-subject-id='${subjectId}']`);
    const subjectName = row.find('td:eq(1)').text().trim();

    fetch(`/api/subjects/${subjectId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: subjectName }),
    })
    .then(response => response.json())
    .then(data => {
        const resultDiv = document.getElementById('subjects_result');
        if (data.message) {
            resultDiv.className = 'alert alert-success mt-2';
            resultDiv.innerText = data.message;
            subjectsTable.row(row).invalidate().draw(false);
        } else {
            resultDiv.className = 'alert alert-danger mt-2';
            resultDiv.innerText = data.error;
        }
        resultDiv.style.display = 'block';
    })
    .catch(error => console.error('Error:', error));
}

function deleteSubject(subjectId) {
    if (!confirm('Are you sure you want to delete this subject?')) return;

    fetch(`/api/subjects/${subjectId}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        const resultDiv = document.getElementById('subjects_result');
        if (data.message) {
            resultDiv.className = 'alert alert-success mt-2';
            resultDiv.innerText = data.message;
            subjectsTable.row($(`tr[data-subject-id='${subjectId}']`)).remove().draw(false);
        } else {
            resultDiv.className = 'alert alert-danger mt-2';
            resultDiv.innerText = data.error;
        }
        resultDiv.style.display = 'block';
    })
    .catch(error => console.error('Error:', error));
}

let attendanceTable;
let subjectsTable;

$(document).ready(function() {
    attendanceTable = $('#attendanceTable').DataTable({
        "ajax": {
            "url": "/api/attendance/fetch",
            "dataSrc": ""
        },
        "columns": [
            { "data": "doc_id" },
            { "data": "student_id" },
            { "data": "name" },
            { "data": "subject_id" },
            { "data": "subject_name" },
            { "data": "timestamp" },
            { "data": "status" },
            { "data": "recorded_by" }
        ]
    });

    // Initialize Subjects DataTable
    subjectsTable = $('#subjectsTable').DataTable({
        "paging": true,
        "searching": true,
        "ordering": true,
        "columnDefs": [
            { "orderable": false, "targets": 2 } // Disable ordering on Actions column
        ]
    });

    loadSubjects();
});

function loadAttendance() {
    const studentId = document.getElementById('filter_student_id').value;
    const subjectId = document.getElementById('filter_subject_id').value;
    const startDate = document.getElementById('filter_start').value;
    const endDate = document.getElementById('filter_end').value;

    const params = new URLSearchParams({
        student_id: studentId,
        subject_id: subjectId,
        start_date: startDate,
        end_date: endDate
    });

    attendanceTable.ajax.url(`/api/attendance/fetch?${params.toString()}`).load();
}

function saveEdits() {
    const data = attendanceTable.rows().data().toArray();

    fetch('/api/attendance/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ attendance: data }),
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message || data.error);
        attendanceTable.ajax.reload();
    })
    .catch(error => console.error('Error:', error));
}

function downloadExcel() {
    window.location.href = "/api/attendance/download_excel";
}

function downloadTemplate() {
    window.location.href = "/api/attendance/download_template";
}

function uploadExcel() {
    const fileInput = document.getElementById('excelFile');
    const file = fileInput.files[0];
    if (!file) {
        alert("Please select a file.");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    fetch('/api/attendance/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message || data.error);
        attendanceTable.ajax.reload();
    })
    .catch(error => console.error('Error:', error));
}

document.getElementById('chatbotToggle').addEventListener('click', function() {
    document.getElementById('chatbotWindow').style.display = 'flex';
});

document.getElementById('chatCloseBtn').addEventListener('click', function() {
    document.getElementById('chatbotWindow').style.display = 'none';
});

document.getElementById('chatSendBtn').addEventListener('click', function() {
    const message = document.getElementById('chatInput').value.trim();
    if (!message) return;

    appendMessage('user', message);
    document.getElementById('chatInput').value = '';

    fetch('/process_prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: message })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            appendMessage('assistant', data.message);
        }
    })
    .catch(error => console.error('Error:', error));
});

function appendMessage(role, message) {
    const messagesDiv = document.getElementById('chatMessages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    msgDiv.innerText = message;
    messagesDiv.appendChild(msgDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function sendAdminCommand() {
    const prompt = document.getElementById('admin_prompt').value.trim();
    if (!prompt) {
        alert('Please enter a command.');
        return;
    }

    fetch('/process_prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt })
    })
    .then(response => response.json())
    .then(data => {
        const resultDiv = document.getElementById('admin_chat_result');
        if (data.message) {
            resultDiv.className = 'alert alert-info mt-3';
            resultDiv.innerText = data.message;
            document.getElementById('admin_prompt').value = '';
        } else {
            resultDiv.className = 'alert alert-danger mt-3';
            resultDiv.innerText = data.error;
        }
    })
    .catch(error => console.error('Error:', error));
}

window.onload = function() {
    loadSubjects();
};