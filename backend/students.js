const db = require('./db');
const { registerFace, recognizeFace } = require('./rekognition');

// Register a student
async function registerStudent(req, res) {
    const { studentName, studentId, image } = req.body;

    try {
        const faceData = await registerFace(image, studentId);

        await db.collection('students').doc(studentId).set({
            name: studentName,
            faceId: faceData.FaceRecords[0].Face.FaceId, // Save the FaceId
        });

        res.json({ success: true, message: 'Student registered successfully' });
    } catch (error) {
        console.error('Error registering student:', error);
        res.status(500).json({ success: false, message: 'Error registering student' });
    }
}

// Recognize a student
async function recognizeStudent(req, res) {
    const { image } = req.body;

    try {
        const faceMatch = await recognizeFace(image);

        if (!faceMatch) {
            return res.status(400).json({ success: false, message: 'Face not recognized' });
        }

        const studentSnapshot = await db.collection('students').where('faceId', '==', faceMatch.Face.FaceId).get();
        if (studentSnapshot.empty) {
            return res.status(400).json({ success: false, message: 'Student not found' });
        }

        const student = studentSnapshot.docs[0].data();
        res.json({
            success: true,
            message: 'Face recognized successfully',
            student,
        });
    } catch (error) {
        console.error('Error recognizing student:', error);
        res.status(500).json({ success: false, message: 'Error recognizing student' });
    }
}

module.exports = { registerStudent, recognizeStudent };