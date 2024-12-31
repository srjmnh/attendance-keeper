const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');
const { registerStudent, recognizeFace } = require('./students');

const app = express();

// Middleware
app.use(bodyParser.json({ limit: '10mb' })); // Allow larger payloads for image data
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, '../frontend'))); // Serve frontend files

// Environment variable for PORT
const PORT = process.env.PORT || 10000;

// Routes
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/index.html')); // Serve the main page
});

// API Endpoint for registering a student
app.post('/register-student', async (req, res) => {
    try {
        await registerStudent(req, res);
    } catch (error) {
        console.error('Error registering student:', error);
        res.status(500).json({ success: false, message: 'Failed to register student' });
    }
});

// API Endpoint for recognizing a face
app.post('/recognize-face', async (req, res) => {
    try {
        await recognizeFace(req, res);
    } catch (error) {
        console.error('Error recognizing face:', error);
        res.status(500).json({ success: false, message: 'Failed to recognize face' });
    }
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});