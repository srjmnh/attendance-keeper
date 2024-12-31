document.addEventListener('DOMContentLoaded', () => {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const context = canvas.getContext('2d');
    const form = document.getElementById('registerForm');
    const result = document.getElementById('result');

    // Start camera
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            video.srcObject = stream;
        })
        .catch(err => {
            console.error('Error accessing camera:', err);
            result.textContent = 'Error accessing camera.';
        });

    form.addEventListener('submit', (event) => {
        event.preventDefault();

        // Capture image from video
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        const faceData = canvas.toDataURL('image/png');

        // Send student data
        const studentName = document.getElementById('studentName').value.trim();
        const studentId = document.getElementById('studentId').value.trim();
        const subject = document.getElementById('subject').value;

        fetch('/register-student', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ studentName, studentId, image: faceData }),
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    result.textContent = 'Student registered successfully!';
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