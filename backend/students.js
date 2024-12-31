const db = require('./db');
const { detectFaces } = require('./azure-face');

async function registerStudent(req, res) {
    const { studentName, studentId, image } = req.body;

    try {
        if (!studentName || !studentId || !image) {
            throw new Error('Missing required fields');
        }

        const faces = await detectFaces(image);
        if (faces.length === 0) {
            return res.status(400).json({ success: false, message: 'No face detected in the image' });
        }

        const faceId = faces[0].faceId; // Store the face ID for later recognition

        // Save student data in Firestore
        const studentDoc = db.collection('students').doc(studentId);
        await studentDoc.set({
            name: studentName,
            faceId,
            image,
        });

        res.json({ success: true, message: 'Student registered successfully' });
    } catch (error) {
        console.error('Error registering student:', error);
        res.status(500).json({ success: false, message: 'Error registering student' });
    }
}

module.exports = { registerStudent };