const express = require('express');
const bodyParser = require('body-parser');
const path = require('path');
const { registerFace, recognizeFace } = require('./rekognition');

const app = express();
const PORT = process.env.PORT || 10000;

app.use(express.static(path.join(__dirname, '../frontend')));
app.use(bodyParser.json({ limit: '10mb' }));

// Routes
app.get('/', (req, res) => res.sendFile(path.join(__dirname, '../frontend/index.html')));
app.get('/register', (req, res) => res.sendFile(path.join(__dirname, '../frontend/register.html')));
app.get('/recognize', (req, res) => res.sendFile(path.join(__dirname, '../frontend/recognize.html')));

// Register student
app.post('/register-student', async (req, res) => {
    const { studentId, name, image } = req.body;

    try {
        await registerFace(image, studentId);
        res.json({ success: true, message: `Student ${name} registered successfully.` });
    } catch (error) {
        console.error('Error registering student:', error);
        res.status(500).json({ success: false, message: 'Failed to register student' });
    }
});

// Recognize student
app.post('/recognize-student', async (req, res) => {
    const { image } = req.body;

    try {
        const studentId = await recognizeFace(image);
        if (studentId) {
            res.json({ success: true, studentId, message: `Recognized student ID: ${studentId}` });
        } else {
            res.json({ success: false, message: 'Face not recognized.' });
        }
    } catch (error) {
        console.error('Error recognizing student:', error);
        res.status(500).json({ success: false, message: 'Failed to recognize face' });
    }
});

app.listen(PORT, () => console.log(`Server running on http://localhost:${PORT}`));