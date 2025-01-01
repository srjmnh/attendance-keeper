const AWS = require('aws-sdk');
const { Buffer } = require('buffer');

// Configure AWS Rekognition
AWS.config.update({
    region: 'us-east-1', // Replace with your AWS region
    accessKeyId: process.env.AWS_ACCESS_KEY_ID,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
});

const rekognition = new AWS.Rekognition();

// Register a face into a collection
async function registerFace(imageBase64, studentId) {
    const params = {
        CollectionId: 'students', // Replace with your collection name
        Image: { Bytes: Buffer.from(imageBase64, 'base64') },
        ExternalImageId: studentId,
    };

    try {
        const response = await rekognition.indexFaces(params).promise();
        console.log('Face indexed:', response);
        return response; // Contains FaceId and metadata
    } catch (error) {
        console.error('Error indexing face:', error);
        throw new Error('Failed to register face');
    }
}

// Recognize a face in the collection
async function recognizeFace(imageBase64) {
    const params = {
        CollectionId: 'students', // Replace with your collection name
        Image: { Bytes: Buffer.from(imageBase64, 'base64') },
        MaxFaces: 1, // Return the best match
    };

    try {
        const response = await rekognition.searchFacesByImage(params).promise();
        console.log('Face recognized:', response);
        return response.FaceMatches[0] || null; // Return the best match or null
    } catch (error) {
        console.error('Error recognizing face:', error);
        throw new Error('Failed to recognize face');
    }
}

module.exports = { registerFace, recognizeFace };