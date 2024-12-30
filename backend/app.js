require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');
const saveAttendance = require('./attendance');
const { addSubject, getSubjects } = require('./subjects');
const { registerStudent } = require('./students');

const app = express();
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, '../frontend')));

// Serve pages
app.get('/', (req, res) => res.sendFile(path.join(__dirname, '../frontend/index.html')));
app.get('/register', (req, res) => res.sendFile(path.join(__dirname, '../frontend/register.html')));
app.get('/add-subject', (req, res) => res.sendFile(path.join(__dirname, '../frontend/add-subject.html')));
app.get('/view', (req, res) => res.sendFile(path.join(__dirname, '../frontend/view.html')));

// APIs
app.post('/register-student', registerStudent);
app.post('/record-attendance', saveAttendance);
app.post('/add-subject', addSubject);
app.get('/get-subjects', getSubjects);

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));