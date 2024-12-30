const db = require('./db');

async function saveAttendance(req, res) {
  const { studentId, subjectCode, image } = req.body;
  const timestamp = new Date().toISOString();
  try {
    const attendanceDoc = db.collection('attendance').doc(subjectCode).collection('records').doc(timestamp);
    await attendanceDoc.set({ studentId, image, timestamp });
    res.json({ success: true });
  } catch (error) {
    console.error('Error saving attendance:', error);
    res.status(500).json({ success: false, message: 'Error saving attendance' });
  }
}

module.exports = saveAttendance;