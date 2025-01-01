const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');
const { registerStudent, recognizeStudent, addSubject, getSubjects, getAttendance } = require('./students');

const app = express();
const PORT = process.env.PORT || 10000;

// Middleware
app.use(bodyParser.json({ limit: '10mb' }));
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, '../frontend')));

// Routes
// Serve index.html as the default page
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/index.html'));
});

// Route for the Register Student page
app.get('/register', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/register.html'));
});

// Route for the Record Attendance page
app.get('/record-attendance', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/attendance.html'));
});

// Route for the Add Subject page
app.get('/add-subject', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/add-subject.html'));
});

// Route for the View Attendance page
app.get('/view', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/view.html'));
});

// API Endpoints
app.post('/register-student', async (req, res) => {
    try {
        await registerStudent(req, res);
    } catch (error) {
        console.error('Error in /register-student:', error);
        res.status(500).json({ success: false, message: 'Failed to register student' });
    }
});

app.post('/mark-attendance', async (req, res) => {
    try {
        await recognizeStudent(req, res);
    } catch (error) {
        console.error('Error in /mark-attendance:', error);
        res.status(500).json({ success: false, message: 'Failed to mark attendance' });
    }
});

app.post('/add-subject', async (req, res) => {
    try {
        await addSubject(req, res);
    } catch (error) {
        console.error('Error in /add-subject:', error);
        res.status(500).json({ success: false, message: 'Failed to add subject' });
    }
});

app.get('/subjects', async (req, res) => {
    try {
        await getSubjects(req, res);
    } catch (error) {
        console.error('Error in /subjects:', error);
        res.status(500).json({ success: false, message: 'Failed to fetch subjects' });
    }
});

app.get('/attendance', async (req, res) => {
    try {
        await getAttendance(req, res);
    } catch (error) {
        console.error('Error in /attendance:', error);
        res.status(500).json({ success: false, message: 'Failed to fetch attendance records' });
    }
});

// Catch-All Route (404 Fallback)
app.use((req, res) => {
    res.status(404).send('Page not found');
});

// Start Server
app.listen(PORT, () => console.log(`Server is running on port ${PORT}`));