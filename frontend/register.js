document.addEventListener('DOMContentLoaded', async () => {
    const video = document.getElementById('camera');
    const registerForm = document.getElementById('registerForm');

    // Start camera
    async function startCamera() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = stream;
        } catch (error) {
            console.error('Error accessing camera:', error);
        }
    }

    // Handle form submission
    registerForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const studentName = document.getElementById('studentName').value;
        const studentId = document.getElementById('studentId').value;

        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
        const image = canvas.toDataURL().split(',')[1]; // Get Base64 image data

        try {
            const response = await fetch('/register-student', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ studentName, studentId, image }),
            });

            const data = await response.json();
            if (data.success) {
                alert('Student registered successfully!');
                registerForm.reset();
            } else {
                alert(`Error: ${data.message}`);
            }
        } catch (error) {
            console.error('Error registering student:', error);
            alert('Failed to register student.');
        }
    });

    await startCamera();
});