require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const fetch = require('node-fetch');
const path = require('path');
const { saveAttendance, getAttendance, registerStudent } = require('./firebase');

const app = express();
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, '../frontend')));

// Serve the main page
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../frontend/index.html'));
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