require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');
const saveAttendance = require('./attendance');
const { registerStudent } = require('./students');
const { addSubject, getSubjects } = require('./subjects');

const app = express();

app.use(bodyParser.json({ limit: '10mb' }));
app.use(bodyParser.urlencoded({ extended: true, limit: '10mb' }));

// Serve static frontend files
app.use(express.static(path.join(__dirname, '../frontend')));

app.get('/', (req, res) => res.sendFile(path.join(__dirname, '../frontend/index.html')));
app.get('/register', (req, res) => res.sendFile(path.join(__dirname, '../frontend/register.html')));
app.get('/view', (req, res) => res.sendFile(path.join(__dirname, '../frontend/view.html')));
app.get('/add-subject', (req, res) => res.sendFile(path.join(__dirname, '../frontend/add-subject.html')));

// API routes
app.post('/register-student', registerStudent);
app.post('/record-attendance', saveAttendance);
app.post('/add-subject', addSubject);
app.get('/get-subjects', getSubjects);

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));