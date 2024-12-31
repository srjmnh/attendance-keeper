document.addEventListener('DOMContentLoaded', () => {
    const video = document.getElementById('camera');
    const canvas = document.getElementById('canvas');
    const captureButton = document.getElementById('captureButton');

    navigator.mediaDevices.getUserMedia({ video: true })
        .then((stream) => {
            video.srcObject = stream;
        })
        .catch((err) => console.error('Camera error:', err));

    captureButton.addEventListener('click', () => {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    });

    document.getElementById('registerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const studentName = document.getElementById('studentName').value;
        const studentId = document.getElementById('studentId').value;
        const image = canvas.toDataURL().split(',')[1];

        const response = await fetch('/register-student', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ studentName, studentId, image }),
        });
        const data = await response.json();
        document.getElementById('result').textContent = data.message;
    });
});