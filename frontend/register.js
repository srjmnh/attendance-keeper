document.addEventListener('DOMContentLoaded', () => {
    const subjectDropdown = document.getElementById('subject');
    const form = document.getElementById('registerForm');
    const result = document.getElementById('result');

    // Fetch subjects from the backend
    function populateSubjects() {
        fetch('/get-subjects')
            .then(response => response.json())
            .then(data => {
                subjectDropdown.innerHTML = '';
                data.forEach(subject => {
                    const option = document.createElement('option');
                    option.value = subject.code;
                    option.textContent = `${subject.name} (${subject.code})`;
                    subjectDropdown.appendChild(option);
                });
            })
            .catch(err => {
                console.error('Error fetching subjects:', err);
                result.textContent = 'Error fetching subjects. Try again later.';
            });
    }

    populateSubjects();

    form.addEventListener('submit', (event) => {
        event.preventDefault();
        const studentName = document.getElementById('studentName').value.trim();
        const studentId = document.getElementById('studentId').value.trim();
        const subject = subjectDropdown.value;

        if (!studentName || !studentId || !subject) {
            result.textContent = 'Please fill in all fields.';
            return;
        }

        const faceData = "base64-face-data-placeholder";

        fetch('/register-student', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ studentName, studentId, image: faceData })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    result.textContent = 'Student registered successfully!';
                    form.reset();
                    populateSubjects();
                } else {
                    result.textContent = `Error: ${data.message}`;
                }
            })
            .catch(err => {
                console.error('Error registering student:', err);
                result.textContent = 'Error registering student.';
            });
    });
});