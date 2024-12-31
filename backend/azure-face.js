const { FaceClient } = require('@azure/ai-face');
const { AzureKeyCredential } = require('@azure/ai-face');

// Initialize Azure Face API client
const faceClient = new FaceClient(
    new AzureKeyCredential(process.env.AZURE_FACE_API_KEY),
    process.env.AZURE_FACE_ENDPOINT
);

// Detect faces
async function detectFaces(imageBase64) {
    try {
        const buffer = Buffer.from(imageBase64, 'base64');
        const response = await faceClient.detectWithStream(buffer, {
            returnFaceAttributes: ["age", "gender", "smile", "emotion"],
            recognitionModel: "recognition_04",
        });

        console.log("Detected faces:", response);
        return response;
    } catch (error) {
        console.error("Error with Azure Face API:", error);
        throw new Error("Azure Face API failed");
    }
}

// Verify faces
async function verifyFaces(faceId1, faceId2) {
    try {
        const response = await faceClient.verifyFaceToFace(faceId1, faceId2);
        console.log("Face verification result:", response);
        return response;
    } catch (error) {
        console.error("Error verifying faces:", error);
        throw new Error("Azure Face API verification failed");
    }
}

module.exports = { detectFaces, verifyFaces };