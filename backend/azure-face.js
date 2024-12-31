const axios = require('axios');

const AZURE_ENDPOINT = process.env.AZURE_FACE_ENDPOINT;
const AZURE_API_KEY = process.env.AZURE_API_KEY;

async function detectFaces(imageBase64) {
    const url = `${AZURE_ENDPOINT}/face/v1.0/detect`;
    const params = {
        recognitionModel: 'recognition_04',
        returnFaceId: true,
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
        return response.data;
    } catch (error) {
        console.error('Error detecting faces:', error.response?.data || error.message);
        throw new Error('Azure Face API face detection failed');
    }
}

module.exports = { detectFaces };