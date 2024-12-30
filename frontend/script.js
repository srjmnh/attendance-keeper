const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const result = document.getElementById('result');
const captureButton = document.getElementById('capture');

navigator.mediaDevices
  .getUserMedia({ video: true })
  .then((stream) => {
    video.srcObject = stream;
  })
  .catch((err) => {
    console.error('Camera access denied:', err);
  });

captureButton.addEventListener('click', () => {
  const context = canvas.getContext('2d');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  context.drawImage(video, 0, 0, canvas.width, canvas.height);

  const image = canvas.toDataURL('image/png');

  fetch('https://<RENDER_BACKEND_URL>/recognize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image })
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        result.textContent = `Welcome, ${data.studentName}! Attendance marked.`;
      } else {
        result.textContent = 'Face not recognized.';
      }
    })
    .catch((err) => {
      console.error('Error recognizing face:', err);
    });
});