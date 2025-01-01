const video = document.getElementById('video');
const canvas = document.createElement('canvas');

// Webcam setup
navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
    video.srcObject = stream;
});

// Capture image
function captureImage() {
    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/png').split(',')[1];
}

// Form submission
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const method = form.querySelector('input[name="method"]:checked').value;
        let imageBase64;

        if (method === 'webcam') {
            imageBase64 = captureImage();
        } else {
            const file = document.querySelector('input[type="file"]').files[0];
            const reader = new FileReader();
            reader.onload = () => {
                imageBase64 = reader.result.split(',')[1];
                sendData(form.id, imageBase64);
            };
            reader.readAsDataURL(file);
            return;
        }
        sendData(form.id, imageBase64);
    });
});

async function sendData(formId, imageBase64) {
    const endpoint = formId === 'register-form' ? '/register-student' : '/recognize-student';
    const payload = formId === 'register-form'
        ? {
              studentId: document.getElementById('studentId').value,
              name: document.getElementById('name').value,
              image: imageBase64,
          }
        : { image: imageBase64 };

    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const result = await response.json();
        alert(result.message);
    } catch (error) {
        console.error(error);
        alert('Operation failed.');
    }
}