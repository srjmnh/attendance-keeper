function getBase64(file, callback) {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => callback(reader.result);
    reader.onerror = (error) => console.error('Error: ', error);
}

function registerUser() {
    const name = document.getElementById('name').value.trim();
    const studentId = document.getElementById('student_id').value.trim();
    const imageInput = document.getElementById('register_image');
    if (name === "" || studentId === "" || imageInput.files.length === 0) {
        alert("Please fill out all fields and upload an image.");
        return;
    }

    // Implement the registration logic (e.g., send data to the server)
    alert("Register functionality is not implemented yet.");
}

function recognizeFace() {
    const subjectSelect = document.getElementById('rec_subject_select').value;
    const imageInput = document.getElementById('rec_image');
    if (imageInput.files.length === 0) {
        alert("Please upload an image.");
        return;
    }

    // Implement the recognition logic (e.g., send data to the server)
    alert("Recognize functionality is not implemented yet.");
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
    const subjectName = document.getElementById('subject_name').value.trim();
    if (subjectName === "") {
        alert("Please enter a subject name.");
        return;
    }

    // Make an AJAX POST request to add the subject
    $.ajax({
        url: '/admin/manage_subjects', // Update with your actual route
        method: 'POST',
        data: { subject_name: subjectName },
        success: function(response) {
            $('#subject_result').removeClass().addClass('alert alert-success').text(response.message).show();
            location.reload(); // Reload to display the new subject
        },
        error: function(xhr) {
            $('#subject_result').removeClass().addClass('alert alert-danger').text(xhr.responseJSON.error).show();
        }
    });
}

function deleteSubject(subjectId) {
    if (!confirm("Are you sure you want to delete this subject?")) return;

    // Make an AJAX DELETE request to delete the subject
    $.ajax({
        url: `/admin/delete_subject/${subjectId}`, // Update with your actual route
        method: 'DELETE',
        success: function(response) {
            $('#subject_result').removeClass().addClass('alert alert-success').text(response.message).show();
            location.reload(); // Reload to remove the deleted subject
        },
        error: function(xhr) {
            $('#subject_result').removeClass().addClass('alert alert-danger').text(xhr.responseJSON.error).show();
        }
    });
}

let attendanceTable;

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
    // Implement functionality to save edited subject names
    // This can involve sending the edited data to the server via AJAX
    alert("Save functionality is not implemented yet.");
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
    const command = document.getElementById('admin_prompt').value.trim();
    if (command === "") {
        alert("Please enter a command.");
        return;
    }

    // Implement the command sending logic (e.g., send data to the server)
    alert(`Command "${command}" sent to Gemini AI.`);
}

window.onload = function() {
    loadSubjects();
};
};