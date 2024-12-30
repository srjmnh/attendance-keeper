const db = require('./db');
const { processFace } = require('./google-vision');

async function saveAttendance(req, res) {
    const { studentId, subjectCode, image } = req.body;
    const timestamp = new Date().toISOString();

    try {
        const faces = await processFace(image);
        if (faces.length === 0) {
            return res.status(400).json({ success: false, message: 'No face detected in the image' });
        }

        const attendanceDoc = db.collection('attendance').doc(subjectCode).collection('records').doc(timestamp);
        await attendanceDoc.set({ studentId, timestamp });
        res.json({ success: true });
    } catch (error) {
        console.error('Error saving attendance:', error);
        res.status(500).json({ success: false, message: 'Error saving attendance' });
    }
}

module.exports = saveAttendance;