let attendanceTable;

function initializeAttendanceTable() {
    attendanceTable = $('#attendanceTable').DataTable({
        "ajax": {
            "url": "/api/attendance/fetch",
            "dataSrc": ""
        },
        "columns": [
            { "data": "doc_id" },
            { "data": "student_id" },
            { "data": "name" },
            { "data": "subject_id" },
            { "data": "subject_name" },
            { "data": "timestamp" },
            { "data": "status" },
            { "data": "recorded_by" }
        ],
        "dom": 'Blfrtip',
        "buttons": [
            'copy', 
            'csv', 
            'excel', 
            {
                extend: 'pdfHtml5',
                orientation: 'landscape',
                pageSize: 'A4'
            }, 
            'print'
        ],
        "order": [[5, "desc"]],
        "pageLength": 25,
        "responsive": true,
        "initComplete": function () {
            // Add individual column searching
            this.api().columns().every(function () {
                let column = this;
                let title = $(column.header()).text();
                let input = $('<input type="text" class="form-control form-control-sm mt-2" placeholder="Search ' + title + '" />')
                    .appendTo($(column.header()))
                    .on('keyup change', function () {
                        if (column.search() !== this.value) {
                            column.search(this.value).draw();
                        }
                    });
            });
        }
    });
}

function initializeSubjectsTable() {
    $('#subjectsTable').DataTable({
        "ajax": {
            "url": "/get_subjects",
            "dataSrc": "data"
        },
        "columns": [
            { 
                "data": "code",
                "render": function(data, type, row) {
                    if (type === 'display' && currentUserRole === 'admin') {
                        return `<input type="text" class="form-control subject-code-input" value="${data || ''}" data-id="${row.id}">`;
                    }
                    return data || '';
                }
            },
            { 
                "data": "name",
                "render": function(data, type, row) {
                    if (type === 'display' && currentUserRole === 'admin') {
                        return `<input type="text" class="form-control subject-name-input" value="${data || ''}" data-id="${row.id}">`;
                    }
                    return data || '';
                }
            },
            { 
                "data": null,
                "orderable": false,
                "render": function(data, type, row) {
                    if (currentUserRole === 'admin') {
                        return `
                            <button class="btn btn-primary btn-sm save-btn" data-id="${row.id}">Save</button>
                            <button class="btn btn-danger btn-sm delete-btn" data-id="${row.id}">Delete</button>
                        `;
                    }
                    return '';
                }
            }
        ],
        "dom": 'Blfrtip',
        "buttons": ['copy', 'csv', 'excel', 'pdf', 'print'],
        "pageLength": 10,
        "responsive": true
    });

    // Event handlers for subject operations
    $('#subjectsTable').on('click', '.save-btn', function() {
        const row = $(this).closest('tr');
        const id = $(this).data('id');
        const code = row.find('.subject-code-input').val().trim();
        const name = row.find('.subject-name-input').val().trim();

        if (!code || !name) {
            alert('Both code and name are required!');
            return;
        }

        $.ajax({
            url: '/api/subjects/update',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ id: id, code: code, name: name }),
            success: function(response) {
                if (response.message) {
                    $('#subject_result').removeClass().addClass('alert alert-success').text(response.message).show();
                    $('#subjectsTable').DataTable().ajax.reload();
                } else {
                    $('#subject_result').removeClass().addClass('alert alert-danger').text(response.error).show();
                }
            },
            error: function(xhr, status, error) {
                $('#subject_result').removeClass().addClass('alert alert-danger').text('Error updating subject: ' + error).show();
            }
        });
    });

    $('#subjectsTable').on('click', '.delete-btn', function() {
        if (confirm('Are you sure you want to delete this subject?')) {
            const id = $(this).data('id');
            $.ajax({
                url: '/api/subjects/delete',
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ id: id }),
                success: function(response) {
                    if (response.message) {
                        $('#subject_result').removeClass().addClass('alert alert-success').text(response.message).show();
                        $('#subjectsTable').DataTable().ajax.reload();
                    } else {
                        $('#subject_result').removeClass().addClass('alert alert-danger').text(response.error).show();
                    }
                },
                error: function(xhr, status, error) {
                    $('#subject_result').removeClass().addClass('alert alert-danger').text('Error deleting subject: ' + error).show();
                }
            });
        }
    });
}

// Document ready function
$(document).ready(function() {
    if ($('#attendanceTable').length) {
        initializeAttendanceTable();
    }
    
    if ($('#subjectsTable').length) {
        initializeSubjectsTable();
    }

    // Add subject button handler
    $('#addSubjectBtn').on('click', function() {
        const code = prompt('Enter subject code (e.g., CSE):');
        if (code) {
            const name = prompt('Enter subject name:');
            if (name) {
                $.ajax({
                    url: '/api/subjects/add',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({ code: code.toUpperCase(), name: name }),
                    success: function(response) {
                        if (response.message) {
                            $('#subject_result').removeClass().addClass('alert alert-success').text(response.message).show();
                            $('#subjectsTable').DataTable().ajax.reload();
                        } else {
                            $('#subject_result').removeClass().addClass('alert alert-danger').text(response.error).show();
                        }
                    },
                    error: function(xhr, status, error) {
                        $('#subject_result').removeClass().addClass('alert alert-danger').text('Error adding subject: ' + error).show();
                    }
                });
            }
        }
    });
});