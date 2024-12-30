const db = require('./db');

async function registerStudent(req, res) {
  const { studentName, studentId, image } = req.body;
  try {
    if (!studentName || !studentId || !image) {
      throw new Error('Missing required fields');
    }
    const studentDoc = db.collection('students').doc(studentId);
    await studentDoc.set({ name: studentName, faceData: image });
    res.json({ success: true });
  } catch (error) {
    console.error('Error registering student:', error);
    res.status(500).json({ success: false, message: 'Error registering student' });
  }
}

module.exports = { registerStudent };