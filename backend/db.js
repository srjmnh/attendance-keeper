const admin = require('firebase-admin');

// Ensure the environment variable is set
if (!process.env.FIREBASE_ADMIN_CREDENTIALS_BASE64) {
    throw new Error('Environment variable FIREBASE_ADMIN_CREDENTIALS_BASE64 is not set');
}

// Decode the Base64 string and parse the JSON
const serviceAccount = JSON.parse(
    Buffer.from(process.env.FIREBASE_ADMIN_CREDENTIALS_BASE64, 'base64').toString('utf-8')
);

// Initialize Firebase
admin.initializeApp({
    credential: admin.credential.cert(serviceAccount),
    databaseURL: 'https://facial-f5096.firebaseio.com' // Replace with your Firebase database URL if different
});

const db = admin.firestore();
module.exports = db;