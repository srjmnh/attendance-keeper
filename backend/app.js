require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');
const { registerStudent } = require('./students');
const { saveAttendance } = require('./attendance');

const app = express();
app.use(bodyParser.json({ limit: '10mb' }));
app.use(express.static(path.join(__dirname, '../frontend')));

// Routes
app.get('/', (req, res) => res.sendFile(path.join(__dirname, '../frontend/index.html')));
app.post('/register-student', registerStudent);
app.post('/record-attendance', saveAttendance);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));