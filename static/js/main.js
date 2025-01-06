// Utility Functions
function getBase64(file, callback) {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => callback(reader.result);
    reader.onerror = (error) => console.error('Error: ', error);
}

// Get CSRF token from meta tag
function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// Add CSRF token to all AJAX requests
$(document).ajaxSend(function(e, xhr, options) {
    const token = getCsrfToken();
    xhr.setRequestHeader("X-CSRFToken", token);
});

// Initialize event handlers when document is ready
$(document).ready(function() {
    // Initialize DataTables if they exist
    if ($.fn.DataTable) {
        if ($('#subjectsTable').length) {
            initializeSubjectsTable();
        }
        if ($('#attendanceTable').length) {
            loadAttendance();
        }
    }

    // Load subjects for recognition dropdown
    if ($('#rec_subject_select').length) {
        loadSubjects();
    }

    // Initialize form handlers with proper validation
    $('#registerForm').on('submit', function(e) {
        e.preventDefault();
        if (this.checkValidity()) {
            registerFace();
        }
        $(this).addClass('was-validated');
    });

    $('#recognizeForm').on('submit', function(e) {
        e.preventDefault();
        if (this.checkValidity()) {
            recognizeFace();
        }
        $(this).addClass('was-validated');
    });
});

/* Register Face */
function registerFace() {
    const name = document.getElementById('reg_name').value;
    const studentId = document.getElementById('reg_student_id').value;
    const file = document.getElementById('reg_image').files[0];

    if (!name || !studentId || !file) {
        alert('Please provide name, student ID, and an image.');
        return;
    }

    const resultDiv = document.getElementById('register_result');
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = 'Processing...';
    resultDiv.className = 'alert alert-info mt-3';

    getBase64(file, (imageData) => {
        fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ 
                name, 
                student_id: studentId, 
                image: imageData 
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            resultDiv.innerHTML = data.message || data.error;
            resultDiv.className = 'alert alert-' + (data.error ? 'danger' : 'success') + ' mt-3';
            
            if (!data.error) {
                document.getElementById('reg_name').value = '';
                document.getElementById('reg_student_id').value = '';
                document.getElementById('reg_image').value = '';
                $('#registerForm').removeClass('was-validated');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            resultDiv.innerHTML = 'An error occurred during registration: ' + error.message;
            resultDiv.className = 'alert alert-danger mt-3';
        });
    });
}

/* Recognize Faces */
function recognizeFace() {
    const file = document.getElementById('rec_image').files[0];
    const subjectId = document.getElementById('rec_subject_select').value;

    if (!file) {
        alert('Please upload an image.');
        return;
    }

    const resultDiv = document.getElementById('recognize_result');
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = 'Processing...';
    resultDiv.className = 'alert alert-info mt-3';

    getBase64(file, (imageData) => {
        fetch('/recognize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ 
                image: imageData,
                subject_id: subjectId 
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.identified_people) {
                let resultHTML = `<p>${data.message || ''}</p>`;
                resultHTML += `<p>Total Faces Detected: ${data.total_faces}</p><ul>`;
                data.identified_people.forEach(person => {
                    resultHTML += `<li><strong>Name:</strong> ${person.name || "Unknown"}, <strong>ID:</strong> ${person.student_id || "N/A"}, <strong>Confidence:</strong> ${person.confidence || "N/A"}%</li>`;
                });
                resultHTML += "</ul>";
                resultDiv.innerHTML = resultHTML;
            } else {
                resultDiv.innerHTML = data.message || data.error;
            }
            
            resultDiv.className = 'alert alert-' + (data.error ? 'danger' : 'success') + ' mt-3';
            
            if (!data.error) {
                document.getElementById('rec_image').value = '';
                $('#recognizeForm').removeClass('was-validated');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            resultDiv.innerHTML = 'An error occurred during recognition: ' + error.message;
            resultDiv.className = 'alert alert-danger mt-3';
        });
    });
}

// Load and display subjects
function loadSubjects() {
    fetch('/api/subjects', {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        const select = document.getElementById('rec_subject_select');
        if (select) {
            select.innerHTML = '<option value="">-- No Subject --</option>';
            data.subjects.forEach(subject => {
                const option = document.createElement('option');
                option.value = subject.id;
                option.textContent = subject.name;
                select.appendChild(option);
            });
        }
    })
    .catch(error => console.error('Error loading subjects:', error));
}

// Add new subject
function addSubject() {
    const subjectName = document.getElementById('subject_name').value.trim();
    if (!subjectName) {
        alert('Please enter a subject name.');
        return;
    }

    fetch('/subjects', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ subject_name: subjectName })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            document.getElementById('subject_name').value = '';
            alert(data.message);
            if ($.fn.DataTable.isDataTable('#subjectsTable')) {
                $('#subjectsTable').DataTable().ajax.reload();
            }
        }
    })
    .catch(error => {
        console.error('Error adding subject:', error);
        alert('An error occurred while adding the subject.');
    });
}

// Initialize subjects table
function initializeSubjectsTable() {
    // Destroy existing DataTable if it exists
    if ($.fn.DataTable.isDataTable('#subjectsTable')) {
        $('#subjectsTable').DataTable().destroy();
    }

    $('#subjectsTable').DataTable({
        ajax: {
            url: '/api/subjects',
            dataSrc: 'subjects',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        },
        columns: [
            { data: 'name', title: 'Subject Name' },
            { 
                data: 'code', 
                title: 'Code',
                defaultContent: ''
            },
            {
                data: null,
                title: 'Actions',
                render: function(data, type, row) {
                    if ($('body').data('role') === 'admin') {
                        return `
                            <button onclick="editSubject('${row.id}', '${row.name}')" class="btn btn-sm btn-primary">
                                <i class="fas fa-edit"></i> Edit
                            </button>
                            <button onclick="deleteSubject('${row.id}')" class="btn btn-sm btn-danger">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        `;
                    }
                    return '';
                }
            }
        ],
        order: [[0, 'asc']],
        responsive: true,
        language: {
            emptyTable: "No subjects available"
        }
    });
}

// Edit subject
function editSubject(id, currentName) {
    const newName = prompt('Enter new subject name:', currentName);
    if (newName && newName.trim() !== '') {
        fetch('/api/subjects/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                subject_id: id,
                name: newName.trim()
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                alert(data.message);
                $('#subjectsTable').DataTable().ajax.reload();
            }
        })
        .catch(error => {
            console.error('Error updating subject:', error);
            alert('An error occurred while updating the subject.');
        });
    }
}

// Delete subject
function deleteSubject(id) {
    if (confirm('Are you sure you want to delete this subject?')) {
        fetch(`/api/subjects/delete/${id}`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                alert(data.message);
                $('#subjectsTable').DataTable().ajax.reload();
            }
        })
        .catch(error => {
            console.error('Error deleting subject:', error);
            alert('An error occurred while deleting the subject.');
        });
    }
}

// Load attendance records
function loadAttendance() {
    const studentId = $('#filter_student_id').val();
    const subjectId = $('#filter_subject_id').val();
    const startDate = $('#filter_start').val();
    const endDate = $('#filter_end').val();

    const url = new URL('/api/attendance', window.location.origin);
    if (studentId) url.searchParams.append('student_id', studentId);
    if (subjectId) url.searchParams.append('subject_id', subjectId);
    if (startDate) url.searchParams.append('start_date', startDate);
    if (endDate) url.searchParams.append('end_date', endDate);

    fetch(url, {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        const table = $('#attendanceTable').DataTable({
            destroy: true,
            data: data,
            columns: [
                { data: 'doc_id' },
                { data: 'student_id' },
                { data: 'name' },
                { data: 'subject_id' },
                { data: 'subject_name' },
                { data: 'timestamp' },
                { data: 'status' }
            ]
        });
    })
    .catch(error => {
        console.error('Error loading attendance:', error);
        alert('An error occurred while loading attendance records.');
    });
}

// Download attendance Excel
function downloadExcel() {
    const studentId = $('#filter_student_id').val();
    const subjectId = $('#filter_subject_id').val();
    const startDate = $('#filter_start').val();
    const endDate = $('#filter_end').val();

    const url = new URL('/api/attendance/download', window.location.origin);
    if (studentId) url.searchParams.append('student_id', studentId);
    if (subjectId) url.searchParams.append('subject_id', subjectId);
    if (startDate) url.searchParams.append('start_date', startDate);
    if (endDate) url.searchParams.append('end_date', endDate);

    window.location.href = url.toString();
}

// Download template
function downloadTemplate() {
    window.location.href = '/api/attendance/template';
}

// Upload Excel
function uploadExcel() {
    const fileInput = document.getElementById('excelFile');
    const file = fileInput.files[0];
    if (!file) {
        alert('Please select a file to upload.');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    fetch('/api/attendance/upload', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            alert(data.message);
            loadAttendance();
            fileInput.value = '';
        }
    })
    .catch(error => {
        console.error('Error uploading Excel:', error);
        alert('An error occurred while uploading the Excel file.');
    });
}

// Save attendance edits
function saveEdits() {
    const table = $('#attendanceTable').DataTable();
    const records = table.data().toArray();

    fetch('/api/attendance/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ records })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            alert(data.message);
            loadAttendance();
        }
    })
    .catch(error => {
        console.error('Error saving edits:', error);
        alert('An error occurred while saving the changes.');
    });
}

// Chat functionality
$(document).ready(function() {
    const chatToggleBtn = $('#chatToggleBtn');
    const chatWindow = $('#chatbotWindow');
    const chatCloseBtn = $('#chatCloseBtn');
    const chatInput = $('#chatInput');
    const chatSendBtn = $('#chatSendBtn');
    const chatMessages = $('#chatMessages');

    chatToggleBtn.click(() => {
        chatWindow.toggle();
    });

    chatCloseBtn.click(() => {
        chatWindow.hide();
    });

    function sendMessage() {
        const message = chatInput.val().trim();
        if (!message) return;

        // Add user message to chat
        chatMessages.append(`
            <div class="message user">
                ${message}
            </div>
        `);
        chatInput.val('');
        chatMessages.scrollTop(chatMessages[0].scrollHeight);

        // Send to backend
        fetch('/process_prompt', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ prompt: message })
        })
        .then(response => response.json())
        .then(data => {
            // Add assistant response to chat
            chatMessages.append(`
                <div class="message assistant">
                    ${data.message}
                </div>
            `);
            chatMessages.scrollTop(chatMessages[0].scrollHeight);
        })
        .catch(error => {
            console.error('Error:', error);
            chatMessages.append(`
                <div class="message assistant error">
                    Sorry, I encountered an error. Please try again.
                </div>
            `);
            chatMessages.scrollTop(chatMessages[0].scrollHeight);
        });
    }

    chatSendBtn.click(sendMessage);
    chatInput.keypress(function(e) {
        if (e.which == 13) {  // Enter key
            sendMessage();
        }
    });
}); 