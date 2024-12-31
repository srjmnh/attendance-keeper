const axios = require('axios');

// Azure Face API configuration
const AZURE_ENDPOINT = process.env.AZURE_FACE_ENDPOINT;
const AZURE_API_KEY = process.env.AZURE_FACE_API_KEY;

// Detect faces using Azure Face API
async function detectFaces(imageBase64) {
    const url = `${AZURE_ENDPOINT}/face/v1.0/detect`;
    const params = {
        returnFaceAttributes: 'age,gender,emotion',
        recognitionModel: 'recognition_04',
        returnRecognitionModel: true,
    };

    try {
        const response = await axios.post(
            url,
            { url: `data:image/png;base64,${imageBase64}` }, // Base64 encoded image
            {
                headers: {
                    'Ocp-Apim-Subscription-Key': AZURE_API_KEY,
                    'Content-Type': 'application/octet-stream',
                },
                params,
            }
        );

        console.log('Face detection response:', response.data);
        return response.data; // List of faces detected
    } catch (error) {
        console.error('Error detecting faces:', error.response?.data || error.message);
        throw new Error('Azure Face API face detection failed');
    }
}

// Compare two faces for recognition
async function verifyFaces(faceId1, faceId2) {
    const url = `${AZURE_ENDPOINT}/face/v1.0/verify`;

    try {
        const response = await axios.post(
            url,
            {
                faceId1,
                faceId2,
            },
            {
                headers: {
                    'Ocp-Apim-Subscription-Key': AZURE_API_KEY,
                    'Content-Type': 'application/json',
                },
            }
        );

        console.log('Face verification response:', response.data);
        return response.data; // Verification result
    } catch (error) {
        console.error('Error verifying faces:', error.response?.data || error.message);
        throw new Error('Azure Face API face verification failed');
    }
}

module.exports = { detectFaces, verifyFaces };