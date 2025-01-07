// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});

// Flash messages
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) return;

    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    alertContainer.appendChild(alert);

    // Auto dismiss after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 150);
    }, 5000);
}

// Form validation
function validateForm(form) {
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;

    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('is-invalid');
        } else {
            input.classList.remove('is-invalid');
        }
    });

    return isValid;
}

// Password strength meter
function checkPasswordStrength(password) {
    let strength = 0;
    const indicators = {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        numbers: /[0-9]/.test(password),
        special: /[^A-Za-z0-9]/.test(password)
    };

    strength += indicators.length ? 1 : 0;
    strength += indicators.uppercase ? 1 : 0;
    strength += indicators.lowercase ? 1 : 0;
    strength += indicators.numbers ? 1 : 0;
    strength += indicators.special ? 1 : 0;

    return {
        score: strength,
        indicators: indicators
    };
}

// Update password strength indicator
function updatePasswordStrength(password, strengthMeter, strengthText) {
    const { score, indicators } = checkPasswordStrength(password);
    const maxScore = 5;
    const percentage = (score / maxScore) * 100;

    strengthMeter.style.width = `${percentage}%`;
    strengthMeter.className = 'progress-bar';

    if (score <= 2) {
        strengthMeter.classList.add('bg-danger');
        strengthText.textContent = 'Weak';
        strengthText.className = 'text-danger';
    } else if (score <= 3) {
        strengthMeter.classList.add('bg-warning');
        strengthText.textContent = 'Moderate';
        strengthText.className = 'text-warning';
    } else {
        strengthMeter.classList.add('bg-success');
        strengthText.textContent = 'Strong';
        strengthText.className = 'text-success';
    }
}

// File upload preview
function handleFileUpload(input, previewElement) {
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            previewElement.src = e.target.result;
            previewElement.style.display = 'block';
        };
        
        reader.readAsDataURL(input.files[0]);
    }
}

// Confirm dialog
function confirmAction(message, callback) {
    const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
    const confirmButton = document.getElementById('confirmButton');
    
    document.getElementById('confirmMessage').textContent = message;
    
    const handleConfirm = () => {
        modal.hide();
        callback();
        confirmButton.removeEventListener('click', handleConfirm);
    };
    
    confirmButton.addEventListener('click', handleConfirm);
    modal.show();
}

// Format date
function formatDate(date) {
    return new Date(date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

// Format time
function formatTime(time) {
    return new Date(time).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Copy to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showAlert('Copied to clipboard!', 'success');
    }).catch(err => {
        showAlert('Failed to copy text', 'danger');
    });
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Handle search input
const handleSearch = debounce((input) => {
    const searchTerm = input.value.toLowerCase();
    const tableRows = document.querySelectorAll('tbody tr');
    
    tableRows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchTerm) ? '' : 'none';
    });
}, 300);

// Export table to CSV
function exportTableToCSV(tableId, filename = 'export.csv') {
    const table = document.getElementById(tableId);
    const rows = table.querySelectorAll('tr');
    const csv = [];
    
    for (const row of rows) {
        const rowData = [];
        const cols = row.querySelectorAll('td, th');
        
        for (const col of cols) {
            rowData.push('"' + col.innerText.replace(/"/g, '""') + '"');
        }
        
        csv.push(rowData.join(','));
    }
    
    const csvContent = 'data:text/csv;charset=utf-8,' + csv.join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Print table
function printTable(tableId) {
    const printContents = document.getElementById(tableId).outerHTML;
    const originalContents = document.body.innerHTML;
    
    document.body.innerHTML = `
        <div class="container mt-4">
            ${printContents}
        </div>
    `;
    
    window.print();
    document.body.innerHTML = originalContents;
    
    // Reinitialize tooltips and popovers
    document.dispatchEvent(new Event('DOMContentLoaded'));
}

// Initialize charts (if Chart.js is included)
function initializeCharts() {
    if (typeof Chart === 'undefined') return;

    // Attendance trend chart
    const attendanceTrendCtx = document.getElementById('attendanceTrendChart');
    if (attendanceTrendCtx) {
        new Chart(attendanceTrendCtx, {
            type: 'line',
            data: {
                labels: [], // Will be populated with dates
                datasets: [{
                    label: 'Attendance Rate',
                    data: [], // Will be populated with attendance rates
                    borderColor: '#4f46e5',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }

    // Subject-wise attendance chart
    const subjectAttendanceCtx = document.getElementById('subjectAttendanceChart');
    if (subjectAttendanceCtx) {
        new Chart(subjectAttendanceCtx, {
            type: 'bar',
            data: {
                labels: [], // Will be populated with subject names
                datasets: [{
                    label: 'Attendance Rate',
                    data: [], // Will be populated with attendance rates
                    backgroundColor: '#4f46e5'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100
                    }
                }
            }
        });
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
}); 