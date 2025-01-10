const admin = require('firebase-admin');
const { Buffer } = require('buffer');
require('dotenv').config();

// Decode the base64-encoded Firebase credentials
const firebaseCredentials = JSON.parse(
    Buffer.from(process.env.FIREBASE_ADMIN_CREDENTIALS_BASE64, 'base64').toString('utf-8')
);

// Initialize Firebase Admin SDK
admin.initializeApp({
    credential: admin.credential.cert(firebaseCredentials),
});

const firestore = admin.firestore();

module.exports = { firestore };