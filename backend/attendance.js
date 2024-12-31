const db = require('./db');
const { recognizeFace } = require('./face-recognition'); // Implement recognition logic here

async function saveAttendance(req, res) {
    const { image, subjectCode } = req.body;
    const timestamp = new Date().toISOString();

    try {
        // Recognize face and get student ID
        const studentId = await recognizeFace(image);
        if (!studentId) {
            return res.status(400).json({ success: false, message: 'Face not recognized' });
        }

        // Mark attendance in Firestore
        const attendanceDoc = db.collection('attendance').doc(subjectCode).collection('records').doc(timestamp);
        await attendanceDoc.set({ studentId, timestamp });

        res.json({ success: true });
    } catch (error) {
        console.error('Error saving attendance:', error);
        res.status(500).json({ success: false, message: 'Error saving attendance' });
    }
}

module.exports = saveAttendance;