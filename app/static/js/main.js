// Utility Functions
function formatDate(dateString) {
    const options = {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

function formatPercentage(value) {
    return `${Math.round(value)}%`;
}

function showLoading(message = 'Loading...') {
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.innerHTML = `
        <div class="text-center">
            <div class="loading-spinner mb-3"></div>
            <p class="text-muted">${message}</p>
        </div>
    `;
    document.body.appendChild(overlay);
}

function hideLoading() {
    const overlay = document.querySelector('.loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

function showToast(message, type = 'success') {
    const Toast = Swal.mixin({
        toast: true,
        position: 'top-end',
        showConfirmButton: false,
        timer: 3000,
        timerProgressBar: true,
        didOpen: (toast) => {
            toast.addEventListener('mouseenter', Swal.stopTimer);
            toast.addEventListener('mouseleave', Swal.resumeTimer);
        }
    });

    Toast.fire({
        icon: type,
        title: message
    });
}

function confirmAction(title, text, confirmButtonText = 'Yes', cancelButtonText = 'No') {
    return Swal.fire({
        title: title,
        text: text,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#4f46e5',
        cancelButtonColor: '#64748b',
        confirmButtonText: confirmButtonText,
        cancelButtonText: cancelButtonText
    });
}

// Form Validation
function validateForm(form) {
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        return false;
    }
    return true;
}

// File Upload
function handleFileUpload(input, previewElement, allowedTypes = ['image/jpeg', 'image/png']) {
    const file = input.files[0];
    
    if (!file) return;
    
    if (!allowedTypes.includes(file.type)) {
        showToast('Please select a valid image file (JPEG/PNG)', 'error');
        input.value = '';
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        previewElement.src = e.target.result;
        previewElement.style.display = 'block';
    };
    reader.readAsDataURL(file);
}

// Camera Functions
function initializeCamera(videoElement) {
    return navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            videoElement.srcObject = stream;
            return new Promise(resolve => {
                videoElement.onloadedmetadata = () => resolve(stream);
            });
        });
}

function captureImage(videoElement, canvasElement) {
    const context = canvasElement.getContext('2d');
    canvasElement.width = videoElement.videoWidth;
    canvasElement.height = videoElement.videoHeight;
    context.drawImage(videoElement, 0, 0);
    return canvasElement.toDataURL('image/jpeg');
}

function stopCamera(stream) {
    stream.getTracks().forEach(track => track.stop());
}

// Data Table Configuration
const dataTableConfig = {
    responsive: true,
    pageLength: 10,
    lengthMenu: [[10, 25, 50, -1], [10, 25, 50, "All"]],
    dom: '<"d-flex justify-content-between align-items-center mb-3"<"d-flex align-items-center"l><"d-flex"f>>t<"d-flex justify-content-between align-items-center mt-3"<"text-muted"i><"d-flex"p>>',
    language: {
        search: "",
        searchPlaceholder: "Search...",
        lengthMenu: "Show _MENU_ entries",
        info: "Showing _START_ to _END_ of _TOTAL_ entries",
        infoEmpty: "Showing 0 to 0 of 0 entries",
        infoFiltered: "(filtered from _MAX_ total entries)",
        paginate: {
            first: '<i class="mdi mdi-chevron-double-left"></i>',
            previous: '<i class="mdi mdi-chevron-left"></i>',
            next: '<i class="mdi mdi-chevron-right"></i>',
            last: '<i class="mdi mdi-chevron-double-right"></i>'
        }
    }
};

// Chart Configuration
const chartConfig = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'bottom',
            labels: {
                usePointStyle: true,
                padding: 20
            }
        },
        tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#fff',
            bodyColor: '#fff',
            padding: 12,
            displayColors: false
        }
    }
};

// Form Submission Handler
function handleFormSubmission(form, url, method = 'POST', successCallback = null) {
    if (!validateForm(form)) return;
    
    const formData = new FormData(form);
    showLoading('Submitting...');
    
    fetch(url, {
        method: method,
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            showToast(data.message || 'Success!');
            if (successCallback) successCallback(data);
        } else {
            showToast(data.message || 'An error occurred', 'error');
        }
    })
    .catch(error => {
        hideLoading();
        showToast('An error occurred while submitting the form', 'error');
        console.error('Form submission error:', error);
    });
}

// AJAX Request Handler
function makeRequest(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    };
    
    if (data) {
        if (method === 'GET') {
            url += '?' + new URLSearchParams(data).toString();
        } else {
            options.body = JSON.stringify(data);
            options.headers['Content-Type'] = 'application/json';
        }
    }
    
    return fetch(url, options)
        .then(response => response.json())
        .catch(error => {
            console.error('Request error:', error);
            throw error;
        });
}

// Event Handlers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips and popovers
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // File upload preview
    const fileInputs = document.querySelectorAll('input[type="file"][data-preview]');
    fileInputs.forEach(input => {
        const previewElement = document.querySelector(input.dataset.preview);
        if (previewElement) {
            input.addEventListener('change', () => handleFileUpload(input, previewElement));
        }
    });

    // Delete confirmation
    const deleteButtons = document.querySelectorAll('[data-delete-url]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const url = this.dataset.deleteUrl;
            const name = this.dataset.deleteName || 'this item';
            
            confirmAction(
                'Delete Confirmation',
                `Are you sure you want to delete ${name}?`,
                'Yes, delete it'
            ).then((result) => {
                if (result.isConfirmed) {
                    showLoading('Deleting...');
                    makeRequest(url, 'DELETE')
                        .then(response => {
                            hideLoading();
                            if (response.success) {
                                showToast(response.message || 'Deleted successfully');
                                if (this.dataset.deleteRedirect) {
                                    window.location.href = this.dataset.deleteRedirect;
                                } else {
                                    const row = this.closest('tr');
                                    if (row) row.remove();
                                }
                            } else {
                                showToast(response.message || 'Failed to delete', 'error');
                            }
                        })
                        .catch(() => {
                            hideLoading();
                            showToast('Failed to delete', 'error');
                        });
                }
            });
        });
    });
}); 