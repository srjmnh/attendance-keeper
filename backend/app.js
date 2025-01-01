const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');
const { registerFace, recognizeFace } = require('./rekognition');
const db = require('./db');

const app = express();
const PORT = process.env.PORT || 10000;

// Middleware to serve static files
app.use(express.static(path.join(__dirname, '../frontend')));
app.use(bodyParser.json({ limit: '10mb' }));

// Routes for serving HTML files
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/attendance.html'));
});

app.get('/register', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/register.html'));
});

app.get('/add-subject', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/add-subject.html'));
});

app.get('/view', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/view.html'));
});

// API Endpoints

// Register a student
app.post('/register-student', async (req, res) => {
    const { name, image } = req.body;
    const studentId = name; // Use the student's name as the ID (can be customized)

    try {
        const faceId = await registerFace(image, studentId);
        await db.collection('students').doc(studentId).set({
            name,
            faceId,
        });
        res.json({ success: true, message: `Student ${name} registered successfully.` });
    } catch (error) {
        console.error('Error registering student:', error);
        res.status(500).json({ success: false, message: 'Failed to register student' });
    }
});

// Mark attendance
app.post('/mark-attendance', async (req, res) => {
    const { subjectCode, image } = req.body;

    try {
        const faceId = await recognizeFace(image);
        if (!faceId) {
            return res.json({ success: false, message: 'Face not recognized' });
        }

        const students = await db.collection('students').get();
        let recognizedStudent = null;

        students.forEach((doc) => {
            if (doc.data().faceId === faceId) {
                recognizedStudent = doc.data();
            }
        });

        if (!recognizedStudent) {
            return res.json({ success: false, message: 'Student not found' });
        }

        // Mark attendance
        const attendance = {
            subjectCode,
            studentName: recognizedStudent.name,
            timestamp: new Date().toISOString(),
        };

        await db.collection('attendance').add(attendance);
        res.json({ success: true, student: recognizedStudent, message: 'Attendance marked successfully.' });
    } catch (error) {
        console.error('Error marking attendance:', error);
        res.status(500).json({ success: false, message: 'Failed to mark attendance' });
    }
});

// Fetch subjects dynamically
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

// Fetch attendance records for a subject
app.get('/attendance', async (req, res) => {
    const { subjectCode } = req.query;

    try {
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
app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});