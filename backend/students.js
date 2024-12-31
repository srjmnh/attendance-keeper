const db = require('./db');
const { detectFaces } = require('./azure-face');

// Register a student with face data
async function registerStudent(req, res) {
    const { studentName, studentId, image } = req.body;

    try {
        const faces = await detectFaces(image);
        if (faces.length === 0) {
            return res.status(400).json({ success: false, message: 'No face detected' });
        }

        // Save face rectangle in Firebase
        const faceData = faces[0].faceRectangle;
        await db.collection('students').doc(studentId).set({
            name: studentName,
            faceData, // Store face rectangle data
        });

        res.json({ success: true, message: 'Student registered successfully' });
    } catch (error) {
        console.error('Error registering student:', error);
        res.status(500).json({ success: false, message: 'Error registering student' });
    }
}

// Recognize a student by comparing face rectangles
async function recognizeFace(req, res) {
    const { image } = req.body;

    try {
        const faces = await detectFaces(image);
        if (faces.length === 0) {
            return res.status(400).json({ success: false, message: 'No face detected' });
        }

        const detectedFaceRectangle = faces[0].faceRectangle;

        // Retrieve all students from Firebase
        const studentsSnapshot = await db.collection('students').get();
        const students = studentsSnapshot.docs.map(doc => ({
            id: doc.id,
            ...doc.data(),
        }));

        // Compare the detected face rectangle with stored rectangles
        const recognizedStudent = students.find(student => {
            const storedRectangle = student.faceData;
            return (
                Math.abs(storedRectangle.width - detectedFaceRectangle.width) < 10 &&
                Math.abs(storedRectangle.height - detectedFaceRectangle.height) < 10
            );
        });

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