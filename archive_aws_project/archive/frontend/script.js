const video = document.getElementById('video');
const canvas = document.createElement('canvas');
const form = document.getElementById('register-form');
const fileSection = document.getElementById('file-section');
const cameraSection = document.getElementById('camera-section');

// Initialize webcam
navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
    video.srcObject = stream;
}).catch(error => {
    console.error('Error accessing webcam:', error);
    alert('Unable to access the webcam. Ensure you’re using HTTPS.');
});

// Switch between webcam and file upload
document.querySelectorAll('input[name="method"]').forEach(option => {
    option.addEventListener('change', () => {
        if (option.value === 'webcam') {
            cameraSection.style.display = 'block';
            fileSection.style.display = 'none';
        } else {
            cameraSection.style.display = 'none';
            fileSection.style.display = 'block';
        }
    });
});

// Handle form submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('name').value;
    const studentId = document.getElementById('studentId').value;
    const method = document.querySelector('input[name="method"]:checked').value;
    let imageBase64;

    if (!name || !studentId) {
        alert('Please fill in all required fields.');
        return;
    }

    if (method === 'webcam') {
        // Capture image from webcam
        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        imageBase64 = canvas.toDataURL('image/png').split(',')[1]; // Remove base64 prefix
    } else {
        // Capture image from file upload
        const file = document.getElementById('imageFile').files[0];
        if (!file) {
            alert('Please select an image file.');
            return;
        }
        const reader = new FileReader();
        reader.onload = async function () {
            imageBase64 = reader.result.split(',')[1]; // Remove base64 prefix
            await registerStudent(name, studentId, imageBase64);
        };
        reader.readAsDataURL(file);
        return;
    }

    await registerStudent(name, studentId, imageBase64);
});

// Register student
async function registerStudent(name, studentId, imageBase64) {
    const payload = { name, studentId, image: imageBase64 };

    try {
        const response = await fetch('/register-student', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        const result = await response.json();
        alert(result.message);
    } catch (error) {
        console.error('Error registering student:', error);
        alert('Failed to register student.');
    }
}