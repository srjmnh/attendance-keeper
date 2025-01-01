const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');
const app = express();
const PORT = process.env.PORT || 10000;

// Middleware
app.use(bodyParser.json({ limit: '10mb' }));
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, '../frontend')));

// Serve the Record Attendance page as the default
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/attendance.html'));
});

// Serve Register Students Page
app.get('/register', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/register.html'));
});

// Serve Add Subjects Page
app.get('/add-subject', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/add-subject.html'));
});

// Serve View Attendance Page
app.get('/view', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/view.html'));
});

// Endpoint to Load Subjects
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

// Endpoint to Mark Attendance
app.post('/mark-attendance', async (req, res) => {
    try {
        const { subjectCode, image } = req.body;

        // Mock student recognition logic
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

// Start the server
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});