const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const result = document.getElementById('result');
const subjectCodeInput = document.getElementById('subjectCode');
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
  const subjectCode = subjectCodeInput.value.trim();
  if (!subjectCode) {
    result.textContent = 'Please enter a subject code.';
    return;
  }

  const context = canvas.getContext('2d');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  context.drawImage(video, 0, 0, canvas.width, canvas.height);

  const image = canvas.toDataURL('image/png');

  fetch('/record-attendance', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subjectCode, image })
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        result.textContent = 'Attendance recorded successfully!';
      } else {
        result.textContent = `Error: ${data.message}`;
      }
    })
    .catch((err) => {
      console.error('Error recording attendance:', err);
    });
});
