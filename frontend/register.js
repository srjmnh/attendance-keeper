document.addEventListener('DOMContentLoaded', async () => {
    const subjectDropdown = document.getElementById('subjectDropdown');
    const video = document.getElementById('camera');
    const canvas = document.getElementById('canvas');
    const captureButton = document.getElementById('captureButton');
    const registerForm = document.getElementById('registerForm');

    // Start the camera
    async function startCamera() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            video.srcObject = stream;
        } catch (error) {
            console.error('Error accessing camera:', error);
        }
    }

    // Fetch subjects dynamically
    async function loadSubjects() {
        try {
            const response = await fetch('/get-subjects');
            const data = await response.json();

            if (data.success) {
                data.subjects.forEach(subject => {
                    const option = document.createElement('option');
                    option.value = subject.id;
                    option.textContent = subject.name;
                    subjectDropdown.appendChild(option);
                });
            } else {
                console.error('Failed to load subjects:', data.message);
            }
        } catch (error) {
            console.error('Error fetching subjects:', error);
        }
    }

    // Capture image from the video feed
    captureButton.addEventListener('click', () => {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    });

    // Handle form submission
    registerForm.addEventListener('submit', async (event) => {
        event.preventDefault();

        const studentName = document.getElementById('studentName').value;
        const studentId = document.getElementById('studentId').value;
        const subjectId = subjectDropdown.value;
        const image = canvas.toDataURL().split(',')[1]; // Get Base64 image data

        if (!studentName || !studentId || !subjectId || !image) {
            alert('Please fill all the fields and capture an image.');
            return;
        }

        try {
            const response = await fetch('/register-student', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ studentName, studentId, subjectId, image }),
            });

            const data = await response.json();
            if (data.success) {
                alert('Student registered successfully!');
                registerForm.reset();
                subjectDropdown.value = ''; // Reset the subject dropdown
            } else {
                alert(`Error: ${data.message}`);
            }
        } catch (error) {
            console.error('Error registering student:', error);
            alert('Failed to register student. Please try again.');
        }
    });

    // Initialize
    await loadSubjects();
    await startCamera();
});