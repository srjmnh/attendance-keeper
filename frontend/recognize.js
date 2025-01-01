const video = document.getElementById('video');
const canvas = document.createElement('canvas');
const form = document.getElementById('recognize-form');
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
    const method = document.querySelector('input[name="method"]:checked').value;
    let imageBase64;

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
            await recognizeStudent(imageBase64);
        };
        reader.readAsDataURL(file);
        return;
    }

    await recognizeStudent(imageBase64);
});

// Recognize student
async function recognizeStudent(imageBase64) {
    const payload = { image: imageBase64 };

    try {
        const response = await fetch('/recognize-student', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        const result = await response.json();
        if (result.success) {
            alert(`Recognized student ID: ${result.studentId}`);
        } else {
            alert('Face not recognized.');
        }
    } catch (error) {
        console.error('Error recognizing student:', error);
        alert('Failed to recognize face.');
    }
}