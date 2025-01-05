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
            li.className = 'list-group-item d-flex justify-content-between align-items-center';
            li.innerHTML = `${subject.name}
                <button onclick="deleteSubject('${subject.id}')" class="btn btn-sm btn-danger ms-2">Delete</button>`;
            subjectsList.appendChild(li);
        });
    })
    .catch(error => console.error('Error:', error));
}

// Function to retrieve CSRF token from meta tag
function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
}

// Initialize Subjects DataTable
function initSubjectsTable() {
    if ($.fn.DataTable.isDataTable('#subjectsTable')) {
        $('#subjectsTable').DataTable().destroy();
    }
    
    subjectsTable = $('#subjectsTable').DataTable({
        pageLength: 10,
        responsive: true,
        columns: [
            { data: 'id' },
            { data: 'code' },
            { 
                data: 'name',
                render: function(data, type, row) {
                    if (type === 'display') {
                        return `<div class="editable" onclick="makeEditable(this)">${data}</div>`;
                    }
                    return data;
                }
            },
            {
                data: null,
                render: function(data, type, row) {
                    return `
                        <button class="btn btn-sm btn-danger" onclick="deleteSubject('${row.id}')">
                            <i class="fas fa-trash"></i> Delete
                        </button>`;
                }
            }
        ]
    });
}

function makeEditable(element) {
    const currentValue = element.textContent;
    element.innerHTML = `<input type="text" class="form-control form-control-sm" value="${currentValue}" 
        onblur="updateSubject(this)" onkeypress="handleKeyPress(event, this)">`;
    element.querySelector('input').focus();
}

function handleKeyPress(event, element) {
    if (event.key === 'Enter') {
        event.preventDefault();
        updateSubject(element);
    }
}

function updateSubject(input) {
    const newValue = input.value;
    const row = $(input).closest('tr');
    const data = subjectsTable.row(row).data();
    
    fetch(`/admin/subjects/edit/${data.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newValue })
    })
    .then(res => res.json())
    .then(response => {
        if (response.error) {
            alert(response.error);
            input.parentElement.innerHTML = data.name;
        } else {
            input.parentElement.innerHTML = newValue;
            data.name = newValue;
            subjectsTable.row(row).data(data).draw(false);
        }
    })
    .catch(err => {
        console.error(err);
        alert('Failed to update subject');
        input.parentElement.innerHTML = data.name;
    });
}

function deleteSubject(subjectId) {
    if (!confirm('Are you sure you want to delete this subject?')) return;
    
    fetch(`/admin/subjects/delete/${subjectId}`, {
        method: 'POST'
    })
    .then(res => res.json())
    .then(response => {
        if (response.error) {
            alert(response.error);
        } else {
            subjectsTable.row($(`#subjectsTable tr[data-id="${subjectId}"]`)).remove().draw();
        }
    })
    .catch(err => {
        console.error(err);
        alert('Failed to delete subject');
    });
}

// Initialize Attendance DataTable
function initAttendanceTable() {
    if ($.fn.DataTable.isDataTable('#attendanceTable')) {
        $('#attendanceTable').DataTable().destroy();
    }
    
    attendanceTable = $('#attendanceTable').DataTable({
        pageLength: 10,
        scrollY: '50vh',
        scrollCollapse: true,
        responsive: true,
        columns: [
            { data: 'doc_id' },
            { 
                data: 'student_id',
                render: function(data, type, row) {
                    if (type === 'display') {
                        return `<div class="editable" onclick="makeEditable(this)">${data}</div>`;
                    }
                    return data;
                }
            },
            { 
                data: 'name',
                render: function(data, type, row) {
                    if (type === 'display') {
                        return `<div class="editable" onclick="makeEditable(this)">${data}</div>`;
                    }
                    return data;
                }
            },
            { data: 'subject_name' },
            { data: 'timestamp' },
            { 
                data: 'status',
                render: function(data, type, row) {
                    if (type === 'display') {
                        return `<select class="form-select form-select-sm" onchange="updateStatus(this, '${row.doc_id}')">
                            <option value="PRESENT" ${data === 'PRESENT' ? 'selected' : ''}>Present</option>
                            <option value="ABSENT" ${data === 'ABSENT' ? 'selected' : ''}>Absent</option>
                        </select>`;
                    }
                    return data;
                }
            },
            {
                data: null,
                render: function(data, type, row) {
                    return `<button class="btn btn-sm btn-danger" onclick="deleteAttendance('${row.doc_id}')">
                        <i class="fas fa-trash"></i>
                    </button>`;
                }
            }
        ]
    });
}

function updateStatus(select, docId) {
    const newStatus = select.value;
    fetch('/api/attendance/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_id: docId, status: newStatus })
    })
    .then(res => res.json())
    .then(response => {
        if (response.error) {
            alert(response.error);
            loadAttendance();
        }
    })
    .catch(err => {
        console.error(err);
        alert('Failed to update status');
        loadAttendance();
    });
}

function deleteAttendance(docId) {
    if (!confirm('Are you sure you want to delete this attendance record?')) return;
    
    fetch(`/api/attendance/delete/${docId}`, {
        method: 'POST'
    })
    .then(res => res.json())
    .then(response => {
        if (response.error) {
            alert(response.error);
        } else {
            attendanceTable.row($(`#attendanceTable tr[data-id="${docId}"]`)).remove().draw();
        }
    })
    .catch(err => {
        console.error(err);
        alert('Failed to delete attendance record');
    });
}

$(document).ready(function() {
    // Initialize DataTables if not already initialized
    if (!$.fn.DataTable.isDataTable('#subjectsTable')) {
        window.subjectsTable = $('#subjectsTable').DataTable();
    }
    if (!$.fn.DataTable.isDataTable('#attendanceTable')) {
        window.attendanceTable = $('#attendanceTable').DataTable();
    }
});

// Edit Subject Function (Admin Only)
function editSubject(subjectId, currentName) {
    const newName = prompt("Enter the new subject name:", currentName);
    if (newName && newName.trim() !== "") {
        fetch(`/admin/subjects/update/${subjectId}`, {  // Updated endpoint to match app.py
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': getCSRFToken(),
            },
            body: new URLSearchParams({
                'name': newName.trim()  // Changed key to match backend
            })
        })
        .then(response => response.json())
        .then(data => {
            const resultDiv = document.getElementById('subject_result');
            if (data.message) {
                resultDiv.className = 'alert alert-success mt-3';
                resultDiv.innerText = data.message;
                subjectsTable.ajax.reload();
                loadSubjectsList();
            } else {
                resultDiv.className = 'alert alert-danger mt-3';
                resultDiv.innerText = data.error;
            }
        })
        .catch(error => console.error('Error updating subject:', error));
    }
}

// Delete Subject Function (Admin Only)
function deleteSubject(subjectId) {
    if (!confirm('Are you sure you want to delete this subject?')) return;

    fetch(`/admin/subjects/delete/${subjectId}`, {  // Updated endpoint to match app.py
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken(),
        },
    })
    .then(response => response.json())
    .then(data => {
        const resultDiv = document.getElementById('subject_result');
        if (data.message) {
            resultDiv.className = 'alert alert-success mt-3';
            resultDiv.innerText = data.message;
            subjectsTable.ajax.reload();
            loadSubjectsList();
        } else {
            resultDiv.className = 'alert alert-danger mt-3';
            resultDiv.innerText = data.error;
        }
    })
    .catch(error => console.error('Error deleting subject:', error));
}

// Function to load the subjects list
function loadSubjectsList() {
    fetch('/api/subjects/fetch')  // Ensure this endpoint exists and returns data in { subjects: [...] } format
    .then(response => response.json())
    .then(data => {
        const subjectsList = document.getElementById('subjects_list');
        subjectsList.innerHTML = '';
        data.subjects.forEach(subject => {
            const li = document.createElement('li');
            li.className = 'list-group-item d-flex justify-content-between align-items-center';
            li.innerHTML = `${subject.name}
                <button onclick="deleteSubject('${subject.id}')" class="btn btn-sm btn-danger ms-2">Delete</button>`;
            subjectsList.appendChild(li);
        });
    })
    .catch(error => console.error('Error:', error));
}

// Other functions like saveEdits, downloadExcel, uploadExcel, chatbot functionalities remain unchanged

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
    loadSubjectsList();
};

function redirectToDashboard() {
    window.location.href = "/";
}

// Add Subject Function (Admin Only)
function addSubject() {
    const subjectName = document.getElementById('subject_name').value.trim();
    if (!subjectName) {
        alert('Subject name cannot be empty.');
        return;
    }

    fetch(`/admin/subjects/add`, {  // Endpoint matches app.py
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCSRFToken(),
        },
        body: new URLSearchParams({
            'subject_name': subjectName
        })
    })
    .then(response => response.json())
    .then(data => {
        const resultDiv = document.getElementById('subject_result');
        if (data.message) {
            resultDiv.className = 'alert alert-success mt-3';
            resultDiv.innerText = data.message;
            subjectsTable.ajax.reload();
            loadSubjectsList();
            document.getElementById('addSubjectForm').reset();
        } else {
            resultDiv.className = 'alert alert-danger mt-3';
            resultDiv.innerText = data.error;
        }
    })
    .catch(error => console.error('Error adding subject:', error));
}
