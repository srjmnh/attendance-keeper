const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');
const { registerStudent, recognizeStudent } = require('./students');

const app = express();
const PORT = process.env.PORT || 10000;

// Middleware
app.use(bodyParser.json({ limit: '10mb' }));
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, '../frontend')));

// Routes
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/index.html'));
});

// Serve the Register page
app.get('/register', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/register.html'));
});

// Register Student Endpoint
app.post('/register-student', async (req, res) => {
    try {
        await registerStudent(req, res);
    } catch (error) {
        console.error('Error in /register-student:', error);
        res.status(500).json({ success: false, message: 'Failed to register student' });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});