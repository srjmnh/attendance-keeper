const axios = require('axios');

// Azure Face API environment variables
const AZURE_ENDPOINT = process.env.AZURE_FACE_ENDPOINT;
const AZURE_API_KEY = process.env.AZURE_API_KEY;

// Detect faces using Azure Face API
async function detectFaces(imageBase64) {
    const url = `${AZURE_ENDPOINT}/face/v1.0/detect`;
    const params = {
        detectionModel: 'detection_03', // Lightweight detection model
        returnFaceId: true, // Only request FaceId
    };

    try {
        const response = await axios.post(
            url,
            Buffer.from(imageBase64, 'base64'),
            {
                headers: {
                    'Ocp-Apim-Subscription-Key': AZURE_API_KEY,
                    'Content-Type': 'application/octet-stream',
                },
                params,
            }
        );
        return response.data; // List of detected faces
    } catch (error) {
        console.error('Error detecting faces:', error.response?.data || error.message);
        throw new Error('Azure Face API face detection failed');
    }
}

module.exports = { detectFaces };