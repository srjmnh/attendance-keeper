// Image preview functionality
function previewImage(input, previewId) {
    const preview = document.getElementById(previewId);
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.style.display = 'block';
        }
        reader.readAsDataURL(input.files[0]);
    }
}

// Add event listeners for image previews
document.getElementById('register_image').addEventListener('change', function() {
    previewImage(this, 'register_image_preview');
});

document.getElementById('recognize_image').addEventListener('change', function() {
    previewImage(this, 'recognize_image_preview');
});

// Enhanced getBase64 function with loading state
function getBase64(file, callback) {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => callback(reader.result);
    reader.onerror = (error) => {
        console.error('Error: ', error);
        showAlert('Error processing image', 'danger');
    };
}

// Show alert message
function showAlert(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.container').firstChild);
    setTimeout(() => alertDiv.remove(), 5000);
}

// Register function with enhanced UI feedback
function register() {
    const name = document.getElementById('name').value;
    const studentId = document.getElementById('student_id').value;
    const file = document.getElementById('register_image').files[0];

    if (!name || !studentId || !file) {
        showAlert('Please provide name, student ID, and an image.', 'warning');
        return;
    }

    const registerBtn = event.target;
    registerBtn.disabled = true;
    registerBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Registering...';

    getBase64(file, (imageData) => {
        fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, student_id: studentId, image: imageData }),
        })
        .then(response => response.json())
        .then(data => {
            const resultDiv = document.getElementById('register_result');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = `
                <i class="fas fa-check-circle me-2"></i>
                ${data.message || data.error}
            `;
            if (!data.error) {
                document.getElementById('name').value = '';
                document.getElementById('student_id').value = '';
                document.getElementById('register_image').value = '';
                document.getElementById('register_image_preview').style.display = 'none';
                updateStats(); // Update dashboard stats
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Registration failed. Please try again.', 'danger');
        })
        .finally(() => {
            registerBtn.disabled = false;
            registerBtn.innerHTML = '<i class="fas fa-save me-2"></i>Register Student';
        });
    });
}

// Recognize function with enhanced UI
function recognize() {
    const file = document.getElementById('recognize_image').files[0];
    const subjectId = document.getElementById('subject_select').value;

    if (!file) {
        showAlert('Please upload an image.', 'warning');
        return;
    }

    const recognizeBtn = event.target;
    recognizeBtn.disabled = true;
    recognizeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';

    const progressBar = document.getElementById('recognizeProgress');
    progressBar.style.display = 'block';
    const progressBarInner = progressBar.querySelector('.progress-bar');

    getBase64(file, (imageData) => {
        fetch('/recognize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData, subject_id: subjectId }),
        })
        .then(response => response.json())
        .then(data => {
            // Update progress
            progressBarInner.style.width = '100%';
            progressBarInner.textContent = '100%';

            // Display results
            const recognizedFaces = document.getElementById('recognizedFaces');
            recognizedFaces.innerHTML = '';

            data.identified_people.forEach(person => {
                const card = document.createElement('div');
                card.className = 'col-md-4 mb-3 slide-up';
                card.innerHTML = `
                    <div class="recognized-face-card card">
                        <div class="card-body">
                            <h5 class="card-title">
                                <i class="fas fa-user me-2"></i>
                                ${person.name || 'Unknown'}
                            </h5>
                            <div class="card-text">
                                <p class="mb-1">
                                    <i class="fas fa-id-card me-2"></i>
                                    Student ID: ${person.student_id || 'N/A'}
                                </p>
                                <p class="mb-1">
                                    <i class="fas fa-percentage me-2"></i>
                                    Confidence: ${person.confidence}%
                                </p>
                                <p class="mb-0">
                                    <i class="fas ${person.student_id ? 'fa-check-circle text-success' : 'fa-times-circle text-danger'} me-2"></i>
                                    Status: ${person.student_id ? 'Attendance Recorded' : 'Not Registered'}
                                </p>
                            </div>
                        </div>
                    </div>
                `;
                recognizedFaces.appendChild(card);
            });

            updateStats(); // Update dashboard stats
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Recognition failed. Please try again.', 'danger');
        })
        .finally(() => {
            recognizeBtn.disabled = false;
            recognizeBtn.innerHTML = '<i class="fas fa-search me-2"></i>Recognize';
            setTimeout(() => {
                progressBar.style.display = 'none';
                progressBarInner.style.width = '0%';
            }, 1000);
        });
    });
}

// Update dashboard stats
function updateStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            document.getElementById('totalStudents').textContent = data.total_students;
            document.getElementById('todayAttendance').textContent = data.today_attendance;
            document.getElementById('totalSubjects').textContent = data.total_subjects;
        })
        .catch(error => console.error('Error updating stats:', error));
}

// Load subjects into select
function loadSubjects() {
    fetch('/get_subjects')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('subject_select');
            select.innerHTML = '<option value="">Select Subject</option>';
            data.subjects.forEach(subject => {
                const option = document.createElement('option');
                option.value = subject.id;
                option.textContent = subject.name;
                select.appendChild(option);
            });
        })
        .catch(error => console.error('Error loading subjects:', error));
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadSubjects();
    updateStats();
});