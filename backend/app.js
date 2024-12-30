require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const fetch = require('node-fetch');
const path = require('path');
const { saveAttendance, getAttendance, registerStudent, addSubject, getSubjects } = require('./firebase');

const app = express();
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, '../frontend')));

// Serve the main page
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/index.html'));
});

// Serve the teacher register page
app.get('/register', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/register.html'));
});

// Serve the teacher view attendance page
app.get('/view', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/view.html'));
});

// Serve the add subject page
app.get('/add-subject', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/add-subject.html'));
});

// Register student
app.post('/register-student', async (req, res) => {
  const { studentName, studentId, image } = req.body;
  try {
    const result = await registerStudent(studentName, studentId, image);
    res.json(result);
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Record attendance
app.post('/record-attendance', async (req, res) => {
  const { studentId, subjectCode, image } = req.body;
  try {
    const timestamp = new Date().toISOString();
    const result = await saveAttendance(studentId, subjectCode, image, timestamp);
    res.json(result);
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Add subject
app.post('/add-subject', async (req, res) => {
  const { subjectCode, subjectName } = req.body;
  try {
    const result = await addSubject(subjectCode, subjectName);
    res.json(result);
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Get subjects
app.get('/get-subjects', async (req, res) => {
  try {
    const subjects = await getSubjects();
    res.json(subjects);
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

// Get attendance records
app.get('/get-attendance', async (req, res) => {
  const { subjectCode } = req.query;
  try {
    const records = await getAttendance(subjectCode);
    res.json(records);
  } catch (error) {
    res.status(500).json({ success: false, message: error.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Backend running on port ${PORT}`);
});