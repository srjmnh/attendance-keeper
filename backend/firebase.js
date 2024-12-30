const admin = require('firebase-admin');

// Decode the base64-encoded Firebase key
const firebaseKeyBase64 = process.env.FIREBASE_KEY_BASE64;
if (!firebaseKeyBase64) {
  throw new Error("FIREBASE_KEY_BASE64 environment variable is not set");
}
const firebaseKey = JSON.parse(Buffer.from(firebaseKeyBase64, 'base64').toString('utf8'));

// Initialize Firebase
admin.initializeApp({
  credential: admin.credential.cert(firebaseKey),
  databaseURL: "https://facial-f5096.firebaseio.com"
});

const db = admin.firestore();

// Save attendance record
async function saveAttendance(studentId, subjectCode, image, timestamp) {
  try {
    const attendanceDoc = db.collection('attendance').doc(subjectCode).collection('records').doc(timestamp);
    await attendanceDoc.set({
      studentId,
      image,
      timestamp
    });
    return { success: true };
  } catch (error) {
    throw new Error('Error saving attendance');
  }
}

// Get attendance records
async function getAttendance(subjectCode) {
  try {
    const records = [];
    const snapshot = await db.collection('attendance').doc(subjectCode).collection('records').get();
    snapshot.forEach(doc => {
      records.push(doc.data());
    });
    return records;
  } catch (error) {
    throw new Error('Error fetching attendance');
  }
}

// Register a student
async function registerStudent(studentName, studentId, image) {
  try {
    const studentDoc = db.collection('students').doc(studentId);
    await studentDoc.set({
      name: studentName,
      faceData: image
    });
    return { success: true };
  } catch (error) {
    throw new Error('Error registering student');
  }
}

module.exports = { saveAttendance, getAttendance, registerStudent };