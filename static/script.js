// Image preview with enhanced animation
function previewImage(input, previewId) {
    const preview = document.getElementById(previewId);
    const container = preview.parentElement;
    
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.style.display = 'none'; // Hide initially for animation
            preview.classList.add('animate__animated', 'animate__fadeIn');
            preview.style.display = 'block'; // Show with animation
            container.classList.add('has-image');
        }
        reader.readAsDataURL(input.files[0]);
    }
}

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

// Modern alert message with animation
function showAlert(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show animate__animated animate__fadeInDown glass-effect`;
    alertDiv.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} me-2"></i>
            <div>${message}</div>
        </div>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.container').firstChild);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.classList.replace('animate__fadeInDown', 'animate__fadeOutUp');
        setTimeout(() => alertDiv.remove(), 1000);
    }, 5000);
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
    registerBtn.innerHTML = `
        <div class="spinner-border spinner-border-sm me-2" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        Registering...
    `;

    getBase64(file, (imageData) => {
        fetch('/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, student_id: studentId, image: imageData }),
        })
        .then(response => response.json())
        .then(data => {
            const resultDiv = document.getElementById('register_result');
            resultDiv.style.display = 'none';
            resultDiv.innerHTML = `
                <i class="fas ${data.error ? 'fa-times-circle text-danger' : 'fa-check-circle text-success'} me-2"></i>
                ${data.message || data.error}
            `;
            resultDiv.classList.add('animate__animated', 'animate__fadeIn');
            resultDiv.style.display = 'block';
            
            if (!data.error) {
                document.getElementById('name').value = '';
                document.getElementById('student_id').value = '';
                document.getElementById('register_image').value = '';
                document.getElementById('register_image_preview').style.display = 'none';
                updateStats();
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
    recognizeBtn.innerHTML = `
        <div class="spinner-border spinner-border-sm me-2" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        Processing...
    `;

    const progressBar = document.getElementById('recognizeProgress');
    const progressBarInner = progressBar.querySelector('.progress-bar');
    progressBar.style.display = 'block';
    progressBarInner.style.width = '0%';
    
    // Simulate progress steps
    let progress = 0;
    const progressInterval = setInterval(() => {
        if (progress < 90) {
            progress += 10;
            progressBarInner.style.width = `${progress}%`;
            progressBarInner.textContent = `${progress}%`;
        }
    }, 500);

    getBase64(file, (imageData) => {
        fetch('/recognize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData, subject_id: subjectId }),
        })
        .then(response => response.json())
        .then(data => {
            clearInterval(progressInterval);
            progressBarInner.style.width = '100%';
            progressBarInner.textContent = '100%';

            const recognizedFaces = document.getElementById('recognizedFaces');
            recognizedFaces.innerHTML = '';

            data.identified_people.forEach((person, index) => {
                const card = document.createElement('div');
                card.className = 'col-md-4 mb-3';
                card.innerHTML = `
                    <div class="recognized-face-card card animate__animated animate__fadeInUp" 
                         style="animation-delay: ${index * 0.1}s">
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
                                <div class="mb-1">
                                    <i class="fas fa-percentage me-2"></i>
                                    Confidence: 
                                    <div class="progress glass-effect">
                                        <div class="progress-bar" role="progressbar" 
                                             style="width: ${person.confidence}%" 
                                             aria-valuenow="${person.confidence}" 
                                             aria-valuemin="0" 
                                             aria-valuemax="100">
                                            ${person.confidence}%
                                        </div>
                                    </div>
                                </div>
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
            updateStats();
        })
        .catch(error => {
            console.error('Error:', error);
            showAlert('Recognition failed. Please try again.', 'danger');
            clearInterval(progressInterval);
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

// Update dashboard stats with animation
function updateStats() {
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            animateNumber('totalStudents', data.total_students);
            animateNumber('todayAttendance', data.today_attendance);
            animateNumber('totalSubjects', data.total_subjects);
        })
        .catch(error => console.error('Error updating stats:', error));
}

// Animate number counting
function animateNumber(elementId, finalNumber) {
    const element = document.getElementById(elementId);
    const start = parseInt(element.textContent);
    const duration = 1000;
    const steps = 20;
    const increment = (finalNumber - start) / steps;
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if ((increment >= 0 && current >= finalNumber) || 
            (increment < 0 && current <= finalNumber)) {
            clearInterval(timer);
            element.textContent = finalNumber;
        } else {
            element.textContent = Math.round(current);
        }
    }, duration / steps);
}

// Load subjects into select with animation
function loadSubjects() {
    fetch('/get_subjects')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('subject_select');
            select.innerHTML = '<option value="">Select Subject</option>';
            data.subjects.forEach((subject, index) => {
                setTimeout(() => {
                    const option = document.createElement('option');
                    option.value = subject.id;
                    option.textContent = subject.name;
                    select.appendChild(option);
                }, index * 100);
            });
        })
        .catch(error => console.error('Error loading subjects:', error));
}

// Event listeners for image previews
document.getElementById('register_image').addEventListener('change', function() {
    previewImage(this, 'register_image_preview');
});

document.getElementById('recognize_image').addEventListener('change', function() {
    previewImage(this, 'recognize_image_preview');
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadSubjects();
    updateStats();
});