const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const result = document.getElementById('result');
const registerForm = document.getElementById('registerForm');

navigator.mediaDevices
  .getUserMedia({ video: true })
  .then((stream) => {
    video.srcObject = stream;
  })
  .catch((err) => {
    console.error('Camera access denied:', err);
  });

registerForm.addEventListener('submit', async (e) => {
  e.preventDefault();

  const studentName = document.getElementById('studentName').value;
  const studentId = document.getElementById('studentId').value;

  const context = canvas.getContext('2d');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  context.drawImage(video, 0, 0, canvas.width, canvas.height);

  const image = canvas.toDataURL('image/png');

  const response = await fetch('/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ studentName, studentId, image })
  });

  const data = await response.json();

  if (data.success) {
    result.textContent = `Registration successful for ${studentName}`;
  } else {
    result.textContent = `Registration failed: ${data.message}`;
  }
});