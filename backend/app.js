const express = require('express');
const bodyParser = require('body-parser');
const { registerFace, recognizeFace } = require('./rekognition');

const app = express();
const PORT = process.env.PORT || 10000;

app.use(bodyParser.json({ limit: '10mb' }));
app.use(express.static('frontend'));

// Register a student
app.post('/register-student', async (req, res) => {
    const { studentId, image } = req.body;

    try {
        await registerFace(image, studentId);
        res.json({ success: true, message: `Student ${studentId} registered successfully.` });
    } catch (error) {
        console.error('Error registering student:', error);
        res.status(500).json({ success: false, message: 'Failed to register student' });
    }
});

// Recognize a student
app.post('/recognize-student', async (req, res) => {
    const { image } = req.body;

    try {
        const studentId = await recognizeFace(image);
        if (studentId) {
            res.json({ success: true, studentId, message: `Recognized student: ${studentId}` });
        } else {
            res.json({ success: false, message: 'Face not recognized' });
        }
    } catch (error) {
        console.error('Error recognizing student:', error);
        res.status(500).json({ success: false, message: 'Failed to recognize face' });
    }
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));