const { ImageAnnotatorClient } = require('@google-cloud/vision');

// Decode the Base64 string from the environment variable
const serviceAccountBase64 = process.env.GOOGLE_APPLICATION_CREDENTIALS_BASE64;
if (!serviceAccountBase64) {
    throw new Error('Environment variable GOOGLE_APPLICATION_CREDENTIALS_BASE64 is not set');
}
const serviceAccount = JSON.parse(Buffer.from(serviceAccountBase64, 'base64').toString('utf-8'));

// Initialize Google Vision API client
const client = new ImageAnnotatorClient({
    credentials: serviceAccount,
});

// Detect faces using Google Vision API
async function detectFaces(image) {
    try {
        const [result] = await client.faceDetection({
            image: { content: image.split(',')[1] }, // Remove `data:image/png;base64,` prefix
        });

        return result.faceAnnotations || [];
    } catch (error) {
        console.error('Error with Google Vision API:', error);
        throw new Error('Google Vision API failed');
    }
}

// Recognize a face by comparing with trained faces
async function recognizeFace(image) {
    try {
        const trainedFaces = await getTrainedFaces();
        const detectedFaces = await detectFaces(image);

        if (detectedFaces.length === 0) {
            return null;
        }

        const recognizedStudent = trainedFaces.find(face =>
            compareFaces(face.faceData, detectedFaces[0])
        );

        return recognizedStudent ? recognizedStudent.studentId : null;
    } catch (error) {
        console.error('Error recognizing face:', error);
        throw new Error('Failed to recognize face');
    }
}

async function getTrainedFaces() {
    const db = require('./db');
    const students = await db.collection('students').get();
    return students.docs.map(doc => ({
        studentId: doc.id,
        faceData: doc.data().faceData,
    }));
}

function compareFaces(trainedFace, detectedFace) {
    console.log('Comparing faces...');
    return true; // Replace with actual comparison logic
}

module.exports = { detectFaces, recognizeFace };