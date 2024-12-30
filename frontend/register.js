document.addEventListener('DOMContentLoaded', () => {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const context = canvas.getContext('2d');
    const subjectDropdown = document.getElementById('subject');
    const form = document.getElementById('registerForm');
    const result = document.getElementById('result');

    // Fetch subjects from the backend
    function populateSubjects() {
        fetch('/get-subjects')
            .then(response => response.json())
            .then(data => {
                subjectDropdown.innerHTML = '';
                data.forEach(subject => {
                    const option = document.createElement('option');
                    option.value = subject.code;
                    option.textContent = `${subject.name} (${subject.code})`;
                    subjectDropdown.appendChild(option);
                });
            })
            .catch(err => {
                console.error('Error fetching subjects:', err);
                result.textContent = 'Error fetching subjects. Try again later.';
            });
    }

    populateSubjects();

    // Request camera access
    function startCamera() {
        navigator.mediaDevices.getUserMedia({ video: true })
            .then((stream) => {
                video.srcObject = stream;
            })
            .catch((err) => {
                console.error('Error accessing camera:', err);
                result.textContent = 'Error accessing camera. Please check permissions.';
            });
    }

    startCamera();

    form.addEventListener('submit', (event) => {
        event.preventDefault();
        const studentName = document.getElementById('studentName').value.trim();
        const studentId = document.getElementById('studentId').value.trim();
        const subject = subjectDropdown.value;

        if (!studentName || !studentId || !subject) {
            result.textContent = 'Please fill in all fields.';
            return;
        }

        // Capture image from the video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const faceData = canvas.toDataURL('image/png');

        fetch('/register-student', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ studentName, studentId, image: faceData })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    result.textContent = 'Student registered successfully!';
                    form.reset();
                    populateSubjects();
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