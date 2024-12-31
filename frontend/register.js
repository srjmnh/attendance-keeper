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
                console.log('Subjects data:', subjects); // Debugging log
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
});