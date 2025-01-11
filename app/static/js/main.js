async function loadTeacherClasses() {
    try {
        const response = await fetch('/admin/api/get_teacher_classes');
        const classes = await response.json();
        const select = document.getElementById('teacherClasses');
        select.innerHTML = ''; // Clear existing options
        classes.forEach(cls => {
            const option = document.createElement('option');
            option.value = cls.id;
            option.textContent = cls.name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading teacher classes:', error);
        showToast('Failed to load classes.', 'error');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const userRole = "{{ user.role }}";
    if (userRole === 'teacher') {
        loadTeacherClasses();
    }
});

function showToast(message, type = 'info', duration = 3000) {
    // Implementation using a library like DaisyUI or custom
    // Example with DaisyUI's toast component
    // Ensure to include toast container in your base.html
    const toastContainer = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type} animate-fade-in`;
    toast.textContent = message;
    toastContainer.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('animate-fade-out');
        toast.addEventListener('animationend', () => toast.remove());
    }, duration);
}

function editStudent(student) {
    // Set form to edit mode
    document.getElementById('modalTitle').textContent = 'Edit Student';
    document.getElementById('studentId').value = student.doc_id;
    document.getElementById('studentName').value = student.name;
    document.getElementById('studentIdInput').value = student.student_id;
    document.getElementById('studentClass').value = student.class;
    document.getElementById('studentDivision').value = student.division;
    
    // Show modal
    document.getElementById('addStudentModal').showModal();
}

async function handleStudentSubmit(event) {
    event.preventDefault();
    
    const studentId = document.getElementById('studentId').value;
    const data = {
        name: document.getElementById('studentName').value,
        student_id: document.getElementById('studentIdInput').value,
        class: document.getElementById('studentClass').value,
        division: document.getElementById('studentDivision').value
    };
    
    try {
        const url = studentId ? `/admin/api/students/${studentId}` : '/admin/api/students';
        const method = studentId ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to save student');
        }
        
        // Success
        showToast('Student saved successfully', 'success');
        document.getElementById('addStudentModal').close();
        location.reload(); // Refresh to show updated data
        
    } catch (error) {
        console.error('Error saving student:', error);
        showToast(error.message, 'error');
    }
}