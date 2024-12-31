const db = require('./db');
const { detectFaces } = require('./azure-face');

// Register student with faceId
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

// Recognize face and return matched student
async function recognizeFace(req, res) {
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

        res.json({ success: true, message: 'Face recognized successfully', student: recognizedStudent });
    } catch (error) {
        console.error('Error recognizing face:', error);
        res.status(500).json({ success: false, message: 'Error recognizing face' });
    }
}

module.exports = { registerStudent, recognizeFace };