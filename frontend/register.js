const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const registerForm = document.getElementById('registerForm');
const result = document.getElementById('result');

// Access the user's camera
navigator.mediaDevices
  .getUserMedia({ video: true })
  .then((stream) => {
    video.srcObject = stream;
  })
  .catch((err) => {
    console.error('Camera access denied:', err);
    result.textContent = 'Error: Camera access denied. Please enable camera permissions.';
  });

// Capture and register student face
registerForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const studentName = document.getElementById('studentName').value.trim();
  const studentId = document.getElementById('studentId').value.trim();

  if (!studentName || !studentId) {
    result.textContent = 'Please enter student details.';
    return;
  }

  const context = canvas.getContext('2d');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  context.drawImage(video, 0, 0, canvas.width, canvas.height);

  const image = canvas.toDataURL('image/png');

  fetch('/register-student', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ studentName, studentId, image })
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        result.textContent = 'Student registered successfully!';
      } else {
        result.textContent = `Error: ${data.message}`;
      }
    })
    .catch((err) => {
      console.error('Error registering student:', err);
      result.textContent = 'Error registering student.';
    });
});