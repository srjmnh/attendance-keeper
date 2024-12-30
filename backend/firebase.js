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

async function saveAttendance(studentName, timestamp) {
  try {
    await db.collection('attendance').add({
      studentName,
      timestamp
    });
    console.log(`Attendance saved for ${studentName}`);
  } catch (error) {
    console.error('Error saving attendance:', error);
  }
}

module.exports = { saveAttendance, db };
