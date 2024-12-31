document.addEventListener('DOMContentLoaded', () => {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const captureButton = document.getElementById('captureButton');
    const form = document.getElementById('registerForm');
    const result = document.getElementById('result');
    const subjectDropdown = document.getElementById('subject');

    let capturedImage = null;

    // Start the video stream
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            video.srcObject = stream;
        })
        .catch(err => {
            console.error('Error accessing camera:', err);
            result.textContent = 'Error accessing camera. Please ensure your browser has permission.';
        });

    // Capture the image
    captureButton.addEventListener('click', () => {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
        capturedImage = canvas.toDataURL('image/png'); // Base64-encoded image
        result.textContent = 'Image captured successfully!';
    });

    // Populate subjects dynamically
    function populateSubjects() {
        fetch('/get-subjects')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch subjects');
                }
                return response.json();
            })
            .then(subjects => {
                subjectDropdown.innerHTML = ''; // Clear existing options
                subjects.forEach(subject => {
                    const option = document.createElement('option');
                    option.value = subject.code;
                    option.textContent = `${subject.name} (${subject.code})`;
                    subjectDropdown.appendChild(option);
                });
            })
            .catch(err => {
                console.error('Error fetching subjects:', err);
                result.textContent = 'Error loading subjects. Please try again later.';
            });
    }

    populateSubjects();

    // Submit form data
    form.addEventListener('submit', (event) => {
        event.preventDefault();

        const studentName = document.getElementById('studentName').value.trim();
        const studentId = document.getElementById('studentId').value.trim();
        const subject = subjectDropdown.value;

        if (!capturedImage) {
            result.textContent = 'Please capture an image before submitting.';
            return;
        }

        fetch('/register-student', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ studentName, studentId, image: capturedImage }),
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    result.textContent = 'Student registered successfully!';
                    form.reset();
                } else {
                    result.textContent = `Error: ${data.message}`;
                }
            })
            .catch(err => {
                console.error('Error registering student:', err);
                result.textContent = 'Error registering student.';
            });
    });
});