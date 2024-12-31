require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');
const { registerStudent, recognizeFace } = require('./students');

const app = express();
app.use(bodyParser.json({ limit: '10mb' }));
app.use(express.static(path.join(__dirname, '../frontend')));

// Serve the register.html file on /register route
app.get('/register', (req, res) => res.sendFile(path.join(__dirname, '../frontend/register.html')));

// Serve the recognize.html file on /recognize route
app.get('/recognize', (req, res) => res.sendFile(path.join(__dirname, '../frontend/recognize.html')));

// API routes
app.post('/register-student', registerStudent);
app.post('/recognize-face', recognizeFace);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));