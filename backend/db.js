const admin = require('firebase-admin');

// Decode the Base64 string from the environment variable
const serviceAccountBase64 = process.env.GOOGLE_APPLICATION_CREDENTIALS_BASE64;
if (!serviceAccountBase64) {
    throw new Error('Environment variable GOOGLE_APPLICATION_CREDENTIALS_BASE64 is not set');
}
const serviceAccount = JSON.parse(Buffer.from(serviceAccountBase64, 'base64').toString('utf-8'));

// Initialize Firebase Admin SDK
admin.initializeApp({
    credential: admin.credential.cert(serviceAccount),
    databaseURL: 'https://your-database-name.firebaseio.com', // Replace with your Firestore URL
});

const db = admin.firestore();
module.exports = db;