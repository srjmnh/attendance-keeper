const admin = require('firebase-admin');

const firebaseKeyBase64 = process.env.FIREBASE_KEY_BASE64;
if (!firebaseKeyBase64) {
  throw new Error('FIREBASE_KEY_BASE64 environment variable is not set');
}
const firebaseKey = JSON.parse(Buffer.from(firebaseKeyBase64, 'base64').toString('utf8'));

admin.initializeApp({
  credential: admin.credential.cert(firebaseKey),
  databaseURL: 'https://facial-f5096.firebaseio.com',
});

const db = admin.firestore();
module.exports = db;