const { ImageAnnotatorClient } = require('@google-cloud/vision');

async function processFace(imageBase64) {
    try {
        const client = new ImageAnnotatorClient();
        const [result] = await client.faceDetection({
            image: { content: imageBase64.split(',')[1] }, // Remove the `data:image/png;base64,` prefix
        });
        return result.faceAnnotations || [];
    } catch (error) {
        console.error('Error with Google Vision API:', error);
        throw new Error('Google Vision API error');
    }
}

module.exports = { processFace };