const AWS = require('aws-sdk');

// Configure AWS Rekognition
AWS.config.update({
    region: process.env.AWS_REGION,
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
});

const rekognition = new AWS.Rekognition();

// Register a face
async function registerFace(imageBase64, studentId) {
    const params = {
        CollectionId: 'students',
        Image: { Bytes: Buffer.from(imageBase64, 'base64') },
        ExternalImageId: studentId,
    };

    try {
        const response = await rekognition.indexFaces(params).promise();
        return response.FaceRecords;
    } catch (error) {
        console.error('Error indexing face:', error);
        throw new Error('Failed to register face');
    }
}

// Recognize a face
async function recognizeFace(imageBase64) {
    const params = {
        CollectionId: 'students',
        Image: { Bytes: Buffer.from(imageBase64, 'base64') },
        MaxFaces: 1,
        FaceMatchThreshold: 90,
    };

    try {
        const response = await rekognition.searchFacesByImage(params).promise();
        if (response.FaceMatches.length > 0) {
            return response.FaceMatches[0].Face.ExternalImageId;
        } else {
            return null;
        }
    } catch (error) {
        console.error('Error recognizing face:', error);
        throw new Error('Failed to recognize face');
    }
}

module.exports = { registerFace, recognizeFace };