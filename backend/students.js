const db = require('./db');

async function registerStudent(req, res) {
    const { studentName, studentId, image } = req.body;
    try {
        if (!studentName || !studentId || !image) {
            throw new Error('Missing required fields');
        }

        // Store student details in Firestore
        const studentDoc = db.collection('students').doc(studentId);
        await studentDoc.set({ name: studentName, faceData: image });

        // Optionally trigger training (can be asynchronous)
        await trainModel();

        res.json({ success: true });
    } catch (error) {
        console.error('Error registering student:', error);
        res.status(500).json({ success: false, message: 'Error registering student' });
    }
}

async function trainModel() {
    try {
        const students = await db.collection('students').get();
        const faces = [];

        students.forEach(doc => {
            const data = doc.data();
            faces.push({ studentId: doc.id, faceData: data.faceData });
        });

        // Perform training logic here (e.g., save face data for recognition)
        console.log('Training model with faces:', faces);
        // Train your model with `faces` here
    } catch (error) {
        console.error('Error training model:', error);
    }
}

module.exports = { registerStudent, trainModel };