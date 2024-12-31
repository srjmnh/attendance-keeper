const admin = require('firebase-admin');

if (!process.env.FIREBASE_ADMIN_CREDENTIALS_BASE64) {
    throw new Error('Environment variable FIREBASE_ADMIN_CREDENTIALS_BASE64 is not set');
}

const serviceAccount = JSON.parse(
    Buffer.from(process.env.FIREBASE_ADMIN_CREDENTIALS_BASE64, 'base64').toString('utf-8')
);

admin.initializeApp({
    credential: admin.credential.cert(serviceAccount),
    databaseURL: 'https://facial-f5096.firebaseio.com',
});

const db = admin.firestore();
module.exports = db;