const db = require('./db');
const { detectFaces } = require('./azure-face');

async function saveAttendance(req, res) {
    const { image } = req.body;

    try {
        const faces = await detectFaces(image);
        if (faces.length === 0) {
            return res.status(400).json({ success: false, message: 'No face detected' });
        }

        const detectedFaceId = faces[0].faceId;

        // Fetch all stored students
        const studentsSnapshot = await db.collection('students').get();
        const students = studentsSnapshot.docs.map(doc => ({
            id: doc.id,
            ...doc.data(),
        }));

        const recognizedStudent = students.find(student => student.faceId === detectedFaceId);

        if (!recognizedStudent) {
            return res.status(400).json({ success: false, message: 'Face not recognized' });
        }

        // Mark attendance
        await db.collection('attendance').add({
            studentId: recognizedStudent.id,
            timestamp: new Date().toISOString(),
        });

        res.json({ success: true, message: 'Attendance marked successfully' });
    } catch (error) {
        console.error('Error saving attendance:', error);
        res.status(500).json({ success: false, message: 'Error saving attendance' });
    }
}

module.exports = { saveAttendance };