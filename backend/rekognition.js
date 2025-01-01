const AWS = require('aws-sdk');
const db = require('./db'); // Firebase database integration

// Configure AWS Rekognition
AWS.config.update({
    region: process.env.AWS_REGION,
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
});

const rekognition = new AWS.Rekognition();

// Register a student's face
async function registerFace(imageBase64, studentId) {
    const params = {
        CollectionId: 'students',
        Image: { Bytes: Buffer.from(imageBase64, 'base64') },
        ExternalImageId: studentId, // Use student ID as unique identifier
    };

    try {
        const response = await rekognition.indexFaces(params).promise();

        // Store face metadata in Firebase
        const faceRecord = response.FaceRecords[0];
        if (faceRecord) {
            await db.collection('students').doc(studentId).set({
                faceId: faceRecord.Face.FaceId,
                name: studentId,
            });
            return faceRecord.Face.FaceId;
        } else {
            throw new Error('No face detected.');
        }
    } catch (error) {
        console.error('Error registering face:', error);
        throw new Error('Failed to register face');
    }
}

// Recognize a face
async function recognizeFace(imageBase64) {
    const params = {
        CollectionId: 'students',
        Image: { Bytes: Buffer.from(imageBase64, 'base64') },
        MaxFaces: 1,
        FaceMatchThreshold: 90, // Confidence threshold
    };

    try {
        const response = await rekognition.searchFacesByImage(params).promise();
        if (response.FaceMatches.length > 0) {
            return response.FaceMatches[0].Face.FaceId; // Return matched face ID
        } else {
            return null;
        }
    } catch (error) {
        console.error('Error recognizing face:', error);
        throw new Error('Failed to recognize face');
    }
}

module.exports = { registerFace, recognizeFace };