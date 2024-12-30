const { v4: uuidv4 } = require('uuid');
const { db } = require('./firebase');

async function registerFace(studentName, studentId, imageBase64) {
  try {
    const studentDoc = db.collection('students').doc(studentId);
    await studentDoc.set({
      name: studentName,
      image: imageBase64, // Store the base64-encoded image
    });
    console.log(`Face registered for student: ${studentName}`);
    return { success: true };
  } catch (error) {
    console.error('Error registering face:', error);
    return { success: false, message: error.message };
  }
}

module.exports = { registerFace };