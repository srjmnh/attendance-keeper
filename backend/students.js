const db = require('./db');
const { detectFaces } = require('./face-recognition');

async function registerStudent(req, res) {
    const { studentName, studentId, image } = req.body;
    try {
        if (!studentName || !studentId || !image) {
            throw new Error('Missing required fields');
        }

        // Detect face using Google Vision API
        const faces = await detectFaces(image);
        if (faces.length === 0) {
            return res.status(400).json({ success: false, message: 'No face detected in the image' });
        }

        // Save student data and face image in Firestore
        const studentDoc = db.collection('students').doc(studentId);
        await studentDoc.set({ name: studentName, faceData: image });

        res.json({ success: true, message: 'Student registered successfully' });
    } catch (error) {
        console.error('Error registering student:', error);
        res.status(500).json({ success: false, message: 'Error registering student' });
    }
}

module.exports = { registerStudent };