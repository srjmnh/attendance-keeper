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
    if (currentUserRole === 'admin') {
        initializeSubjectsTable();
    } else {
        loadSubjectsList();
    }
}

function initializeSubjectsTable() {
    $('#subjectsTable').DataTable({
        "ajax": {
            "url": "/get_subjects",
            "dataSrc": "data",
            "error": function(xhr, error, thrown) {
                console.error('Error loading subjects:', error);
                alert('Error loading subjects. Please try again.');
            }
        },
        "columns": [
            { 
                "data": "code",
                "render": function(data, type, row) {
                    if (type === 'display' && currentUserRole === 'admin') {
                        return `<input type="text" class="form-control subject-code-input" value="${data}" data-id="${row.id}">`;
                    }
                    return data;
                }
            },
            { 
                "data": "name",
                "render": function(data, type, row) {
                    if (type === 'display' && currentUserRole === 'admin') {
                        return `<input type="text" class="form-control subject-name-input" value="${data}" data-id="${row.id}">`;
                    }
                    return data;
                }
            },
            { 
                "data": null,
                "orderable": false,
                "visible": currentUserRole === 'admin',
                "render": function(data, type, row) {
                    return `
                        <button class="btn btn-primary btn-sm save-btn" data-id="${row.id}">Save</button>
                        <button class="btn btn-danger btn-sm delete-btn" data-id="${row.id}">Delete</button>
                    `;
                }
            }
        ],
        "order": [[0, 'asc']],
        "pageLength": 10,
        "responsive": true,
        "destroy": true
    });

    $(document).on('click', '.save-btn', function() {
        const subjectId = $(this).data('id');
        const row = $(this).closest('tr');
        const newName = row.find('.subject-name-input').val().trim();
        
        if (!newName) {
            alert('Subject name cannot be empty.');
            return;
        }
        
        saveSubjectEdit(subjectId, newName);
    });
    
    $(document).on('click', '.delete-btn', function() {
        const subjectId = $(this).data('id');
        deleteSubject(subjectId);
    });
}

function loadSubjectsList() {
    fetch('/get_subjects')
    .then(response => response.json())
    .then(data => {
        if (data.subjects) {
            const subjectsList = document.getElementById('subjects_list');
            subjectsList.innerHTML = '';
            data.subjects.forEach(subject => {
                const li = document.createElement('li');
                li.className = 'list-group-item';
                li.innerText = `${subject.code} - ${subject.name}`;
                subjectsList.appendChild(li);
            });
        } else if (data.error) {
            alert(`Error: ${data.error}`);
        }
    })
    .catch(error => console.error('Error:', error));
}

function saveSubjectEdit(subjectId, newName) {
    fetch('/api/subjects/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: subjectId, name: newName }),
    })
    .then(response => response.json())
    .then(data => {
        const resultDiv = document.getElementById('subject_result');
        if (data.message) {
            resultDiv.className = 'alert alert-success';
            resultDiv.innerText = data.message;
            resultDiv.style.display = 'block';
            $('#subjectsTable').DataTable().ajax.reload();
        } else {
            resultDiv.className = 'alert alert-danger';
            resultDiv.innerText = data.error;
            resultDiv.style.display = 'block';
        }
    })
    .catch(error => console.error('Error:', error));
}

function deleteSubject(subjectId) {
    if (!confirm('Are you sure you want to delete this subject?')) return;

    fetch('/api/subjects/delete', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: subjectId }),
    })
    .then(response => response.json())
    .then(data => {
        const resultDiv = document.getElementById('subject_result');
        if (data.message) {
            resultDiv.className = 'alert alert-success';
            resultDiv.innerText = data.message;
            resultDiv.style.display = 'block';
            $('#subjectsTable').DataTable().ajax.reload();
        } else {
            resultDiv.className = 'alert alert-danger';
            resultDiv.innerText = data.error;
            resultDiv.style.display = 'block';
        }
    })
    .catch(error => console.error('Error:', error));
}

$(document).on('click', '#addSubjectBtn', function() {
    const name = prompt('Enter subject name:');
    if (name) {
        const code = name.substring(0, 3).toUpperCase();
        fetch('/api/subjects/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name: name, code: code }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                $('#subject_result').removeClass().addClass('alert alert-success').text(data.message).show();
                $('#subjectsTable').DataTable().ajax.reload();
            } else {
                $('#subject_result').removeClass().addClass('alert alert-danger').text(data.error).show();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            $('#subject_result').removeClass().addClass('alert alert-danger').text('An error occurred').show();
        });
    }
});

let attendanceTable;

$(document).ready(function() {
    const currentUserRole = /* You need to set this variable based on user role.
                                This can be done by rendering a script variable with the role from Flask.
                                For example, in your base.html or dashboard.html, add:
                                <script>
                                    var currentUserRole = "{{ role }}";
                                </script>
                                Then, it can be accessed here.
                             */ 'admin'; // Placeholder, replace with actual role.

    // Initialize DataTables
    if (document.getElementById('attendanceTable')) {
        initializeAttendanceTable();
    }
    
    if (document.getElementById('subjectsTable')) {
        initializeSubjectsTable();
    }

    // Add event handlers for subject operations
    $(document).on('click', '.save-btn', function() {
        const row = $(this).closest('tr');
        const subjectId = $(this).data('id');
        const newCode = row.find('.subject-code-input').val().trim();
        const newName = row.find('.subject-name-input').val().trim();
        
        if (!newName || !newCode) {
            alert('Subject code and name cannot be empty.');
            return;
        }
        
        saveSubjectEdit(subjectId, newCode, newName);
    });
    
    $(document).on('click', '.delete-btn', function() {
        if (confirm('Are you sure you want to delete this subject?')) {
            const subjectId = $(this).data('id');
            deleteSubject(subjectId);
        }
    });

    // Add subject button handler
    $('#addSubjectBtn').on('click', function() {
        const name = prompt('Enter subject name:');
        if (name) {
            const code = name.substring(0, 3).toUpperCase();
            addSubject(code, name);
        }
    });

    loadSubjects();

    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.forEach(function(tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl)
    });
});

function initializeAttendanceTable() {
    attendanceTable = $('#attendanceTable').DataTable({
        "ajax": {
            "url": "/api/attendance/fetch",
            "dataSrc": "",
            "error": function(xhr, error, thrown) {
                console.error('Error loading attendance data:', error);
                alert('Error loading attendance data. Please try again.');
            }
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
        ],
        "order": [[5, 'desc']], // Sort by timestamp by default
        "pageLength": 10,
        "responsive": true,
        "dom": 'Bfrtip',
        "buttons": ['copy', 'csv', 'excel', 'pdf', 'print'],
        "initComplete": function () {
            this.api().columns().every(function () {
                let column = this;
                let title = $(column.header()).text();
                // Create the filter input
                let input = $('<input type="text" class="form-control form-control-sm" placeholder="Filter ' + title + '" />')
                    .appendTo($(column.header()))
                    .on('keyup change', function () {
                        if (column.search() !== this.value) {
                            column.search(this.value).draw();
                        }
                    });
            });
        }
    });
}

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
        alert('Please select an Excel file.');
        return;
    }

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