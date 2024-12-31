const db = require('./db');
const { detectFaces, verifyFaces } = require('./azure-face');

async function saveAttendance(req, res) {
    const { image, subjectCode } = req.body;

    try {
        const liveFaces = await detectFaces(image);
        if (liveFaces.length === 0) {
            return res.status(400).json({ success: false, message: 'No face detected' });
        }

        const liveFaceId = liveFaces[0].faceId;
        const students = await db.collection('students').get();

        let recognizedStudent = null;
        for (const studentDoc of students.docs) {
            const student = studentDoc.data();
            const result = await verifyFaces(liveFaceId, student.faceId);

            if (result.isIdentical && result.confidence > 0.9) {
                recognizedStudent = studentDoc.id;
                break;
            }
        }

        if (!recognizedStudent) {
            return res.status(400).json({ success: false, message: 'Face not recognized' });
        }

        await db
            .collection('attendance')
            .doc(subjectCode)
            .collection('records')
            .doc()
            .set({ studentId: recognizedStudent, timestamp: new Date().toISOString() });

        res.json({ success: true, message: 'Attendance marked successfully' });
    } catch (error) {
        console.error('Error saving attendance:', error);
        res.status(500).json({ success: false, message: 'Error saving attendance' });
    }
}

module.exports = saveAttendance;