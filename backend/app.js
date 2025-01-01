const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');
const app = express();
const PORT = process.env.PORT || 10000;

// Middleware
app.use(bodyParser.json({ limit: '10mb' }));
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, '../frontend')));

// Routes for serving pages
app.get('/', (req, res) => res.sendFile(path.join(__dirname, '../frontend/attendance.html')));
app.get('/register', (req, res) => res.sendFile(path.join(__dirname, '../frontend/register.html')));
app.get('/add-subject', (req, res) => res.sendFile(path.join(__dirname, '../frontend/add-subject.html')));
app.get('/view', (req, res) => res.sendFile(path.join(__dirname, '../frontend/view.html')));

// Endpoint to load subjects dynamically
app.get('/subjects', async (req, res) => {
    try {
        const subjects = [
            { subjectName: 'Mathematics', subjectCode: 'MATH101' },
            { subjectName: 'Science', subjectCode: 'SCI101' },
        ];
        res.json(subjects);
    } catch (error) {
        console.error('Error fetching subjects:', error);
        res.status(500).json({ success: false, message: 'Failed to fetch subjects' });
    }
});

// Endpoint to register a student
app.post('/register-student', async (req, res) => {
    try {
        const { name, image } = req.body;

        // Mock registration logic
        console.log(`Registered student: ${name}`);
        res.json({ success: true, message: `Student ${name} registered successfully.` });
    } catch (error) {
        console.error('Error registering student:', error);
        res.status(500).json({ success: false, message: 'Failed to register student' });
    }
});

// Endpoint to mark attendance
app.post('/mark-attendance', async (req, res) => {
    try {
        const { subjectCode, image } = req.body;

        // Mock recognition logic
        const recognizedStudent = { studentId: '12345', name: 'John Doe' };

        if (recognizedStudent) {
            console.log(`Attendance marked for ${recognizedStudent.name} in ${subjectCode}`);
            res.json({ success: true, student: recognizedStudent });
        } else {
            res.json({ success: false, message: 'Face not recognized' });
        }
    } catch (error) {
        console.error('Error marking attendance:', error);
        res.status(500).json({ success: false, message: 'Failed to mark attendance' });
    }
});

// Endpoint to view attendance for a subject
app.get('/attendance', async (req, res) => {
    try {
        const { subjectCode } = req.query;

        // Mock attendance data
        const attendance = [
            { studentName: 'John Doe', timestamp: '2025-01-01 09:00:00' },
            { studentName: 'Jane Smith', timestamp: '2025-01-01 09:05:00' },
        ];

        res.json({ success: true, attendance });
    } catch (error) {
        console.error('Error fetching attendance:', error);
        res.status(500).json({ success: false, message: 'Failed to fetch attendance' });
    }
});

// Start the server
app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`));