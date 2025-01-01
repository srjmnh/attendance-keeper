const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const form = document.getElementById('register-form');

// Initialize webcam
navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
    video.srcObject = stream;
}).catch(error => {
    console.error('Error accessing webcam:', error);
});

// Form submission logic
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('name').value.trim();
    const studentId = document.getElementById('studentId').value.trim();
    const method = document.querySelector('input[name="method"]:checked').value;
    let imageBase64;

    if (method === 'webcam') {
        const context = canvas.getContext('2d');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        imageBase64 = canvas.toDataURL('image/png').split(',')[1];
    } else {
        const file = document.getElementById('imageFile').files[0];
        const reader = new FileReader();
        reader.onload = async function () {
            imageBase64 = reader.result.split(',')[1];
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
    }
}