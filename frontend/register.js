document.addEventListener('DOMContentLoaded', async () => {
    const registerForm = document.getElementById('registerForm');
    const imageSource = document.getElementById('imageSource');
    const webcamContainer = document.getElementById('webcamContainer');
    const fileContainer = document.getElementById('fileContainer');
    const video = document.getElementById('camera');
    let stream;

    // Handle image source change
    imageSource.addEventListener('change', () => {
        const source = imageSource.value;
        if (source === 'webcam') {
            webcamContainer.style.display = 'block';
            fileContainer.style.display = 'none';
            startCamera();
        } else {
            webcamContainer.style.display = 'none';
            fileContainer.style.display = 'block';
            if (stream) stream.getTracks().forEach(track => track.stop());
        }
    });

    // Start the camera
    async function startCamera() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = stream;
        } catch (error) {
            console.error('Error accessing camera:', error);
        }
    }

    // Submit the form
    registerForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const studentName = document.getElementById('studentName').value;
        const studentId = document.getElementById('studentId').value;
        let image;

        if (imageSource.value === 'webcam') {
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
            image = canvas.toDataURL().split(',')[1]; // Base64 image
        } else {
            const file = document.getElementById('fileUpload').files[0];
            const reader = new FileReader();
            reader.onload = async () => {
                image = reader.result.split(',')[1];
                await submitData(studentName, studentId, image);
            };
            reader.readAsDataURL(file);
            return;
        }

        await submitData(studentName, studentId, image);
    });

    async function submitData(studentName, studentId, image) {
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
    }
});