const db = require('./db');
const { detectFaces } = require('./azure-face');

// Register a student with FaceId
async function registerStudent(req, res) {
    const { studentName, studentId, image } = req.body;

    try {
        const faces = await detectFaces(image);
        if (faces.length === 0) {
            return res.status(400).json({ success: false, message: 'No face detected' });
        }

        const faceId = faces[0].faceId; // Save the FaceId for later recognition

        await db.collection('students').doc(studentId).set({
            name: studentName,
            faceId, // Save the FaceId in Firebase
        });

        res.json({ success: true, message: 'Student registered successfully' });
    } catch (error) {
        console.error('Error registering student:', error);
        res.status(500).json({ success: false, message: 'Error registering student' });
    }
}

// Recognize a student by comparing FaceIds
async function recognizeFace(req, res) {
    const { image } = req.body;

    try {
        const faces = await detectFaces(image);
        if (faces.length === 0) {
            return res.status(400).json({ success: false, message: 'No face detected' });
        }

        const detectedFaceId = faces[0].faceId;

        // Retrieve all students from Firebase
        const studentsSnapshot = await db.collection('students').get();
        const students = studentsSnapshot.docs.map(doc => ({
            id: doc.id,
            ...doc.data(),
        }));

        // Compare the detected FaceId with stored FaceIds
        const recognizedStudent = students.find(student => student.faceId === detectedFaceId);

        if (!recognizedStudent) {
            return res.status(400).json({ success: false, message: 'Face not recognized' });
        }

        res.json({
            success: true,
            message: 'Face recognized successfully',
            student: recognizedStudent,
        });
    } catch (error) {
        console.error('Error recognizing face:', error);
        res.status(500).json({ success: false, message: 'Error recognizing face' });
    }
}

module.exports = { registerStudent, recognizeFace };