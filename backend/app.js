const express = require('express');
const bodyParser = require('body-parser');
const { registerFace, recognizeFace } = require('./rekognition');
const db = require('./db');

const app = express();
const PORT = process.env.PORT || 10000;

app.use(bodyParser.json({ limit: '10mb' }));

// Register a student
app.post('/register-student', async (req, res) => {
    const { name, image } = req.body;
    const studentId = name; // Use the student's name as the ID (changeable)

    try {
        const faceId = await registerFace(image, studentId);
        await db.collection('students').doc(studentId).set({
            name,
            faceId,
        });
        res.json({ success: true, message: `Student ${name} registered successfully.` });
    } catch (error) {
        console.error('Error registering student:', error);
        res.status(500).json({ success: false, message: 'Failed to register student' });
    }
});

// Mark attendance
app.post('/mark-attendance', async (req, res) => {
    const { subjectCode, image } = req.body;

    try {
        const faceId = await recognizeFace(image);
        if (!faceId) {
            return res.json({ success: false, message: 'Face not recognized' });
        }

        const students = await db.collection('students').get();
        let recognizedStudent = null;

        students.forEach((doc) => {
            if (doc.data().faceId === faceId) {
                recognizedStudent = doc.data();
            }
        });

        if (!recognizedStudent) {
            return res.json({ success: false, message: 'Student not found' });
        }

        // Mark attendance
        const attendance = {
            subjectCode,
            studentName: recognizedStudent.name,
            timestamp: new Date().toISOString(),
        };

        await db.collection('attendance').add(attendance);
        res.json({ success: true, student: recognizedStudent, message: 'Attendance marked successfully.' });
    } catch (error) {
        console.error('Error marking attendance:', error);
        res.status(500).json({ success: false, message: 'Failed to mark attendance' });
    }
});

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));