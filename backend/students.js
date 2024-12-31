const db = require('./db');
const { detectFaces } = require('./azure-face');

async function registerStudent(req, res) {
    const { studentName, studentId, image } = req.body;

    try {
        const faces = await detectFaces(image);
        if (faces.length === 0) {
            return res.status(400).json({ success: false, message: 'No face detected' });
        }

        const faceId = faces[0].faceId;

        await db.collection('students').doc(studentId).set({
            name: studentName,
            faceId,
        });

        res.json({ success: true, message: 'Student registered successfully' });
    } catch (error) {
        console.error('Error registering student:', error);
        res.status(500).json({ success: false, message: 'Error registering student' });
    }
}

module.exports = { registerStudent };