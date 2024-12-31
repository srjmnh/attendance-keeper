document.addEventListener('DOMContentLoaded', () => {
    const subjectDropdown = document.getElementById('subject');
    const result = document.getElementById('result');

    // Function to fetch and populate subjects
    function populateSubjects() {
        fetch('/get-subjects')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch subjects');
                }
                return response.json();
            })
            .then(subjects => {
                subjectDropdown.innerHTML = ''; // Clear existing options
                subjects.forEach(subject => {
                    const option = document.createElement('option');
                    option.value = subject.code;
                    option.textContent = `${subject.name} (${subject.code})`;
                    subjectDropdown.appendChild(option);
                });
            })
            .catch(err => {
                console.error('Error fetching subjects:', err);
                result.textContent = 'Error loading subjects. Please try again later.';
            });
    }

    populateSubjects();

    // Submit form data
    document.getElementById('registerForm').addEventListener('submit', (event) => {
        event.preventDefault();

        const studentName = document.getElementById('studentName').value.trim();
        const studentId = document.getElementById('studentId').value.trim();
        const subject = subjectDropdown.value;

        fetch('/register-student', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ studentName, studentId, subject }),
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    result.textContent = 'Student registered successfully!';
                    document.getElementById('registerForm').reset();
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