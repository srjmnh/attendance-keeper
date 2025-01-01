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

// Serve other pages
app.get('/register', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/register.html'));
});

app.get('/add-subject', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/add-subject.html'));
});

app.get('/view', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/view.html'));
});

// Dynamic Subject Loading Endpoint
app.get('/subjects', async (req, res) => {
    try {
        // Mock response - Replace with Firestore or database logic
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

// Mark Attendance Endpoint
app.post('/mark-attendance', async (req, res) => {
    try {
        const { subjectCode, image } = req.body;

        // Mock recognition logic - Replace with actual implementation
        const recognizedStudent = { studentId: '12345', name: 'John Doe' };

        if (recognizedStudent) {
            // Log attendance - Replace with Firestore or database logic
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
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
