function getBase64(file, callback) {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => callback(reader.result);
    reader.onerror = (error) => console.error('Error: ', error);
}

function register() {
    const name = document.getElementById('name').value;
    const studentId = document.getElementById('student_id').value;
    const file = document.getElementById('register_image').files[0];

    if (!name || !studentId || !file) {
        alert('Please provide name, student ID, and an image.');
        return;
    }

    getBase64(file, (imageData) => {
        fetch('/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name, student_id: studentId, image: imageData }),
        })
        .then(response => response.json())
        .then(data => {
            document.getElementById('register_result').innerText = data.message || data.error;
        })
        .catch(error => console.error('Error:', error));
    });
}

function recognize() {
    const file = document.getElementById('recognize_image').files[0];

    if (!file) {
        alert('Please upload an image.');
        return;
    }

    getBase64(file, (imageData) => {
        fetch('/recognize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ image: imageData }),
        })
        .then(response => response.json())
        .then(data => {
            const resultText = data.message || data.error;
            document.getElementById('recognize_result').innerText = resultText;

            if (data.identified_people) {
                let resultHTML = "<ul>";
                data.identified_people.forEach(person => {
                    resultHTML += `<li><strong>Name:</strong> ${person.name}, <strong>ID:</strong> ${person.student_id}, <strong>Confidence:</strong> ${person.confidence.toFixed(2)}%</li>`;
                });
                resultHTML += "</ul>";
                document.getElementById('recognize_result').innerHTML = resultHTML;
            }
        })
        .catch(error => console.error('Error:', error));
    });
}