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