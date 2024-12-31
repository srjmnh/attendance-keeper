const { ImageAnnotatorClient } = require('@google-cloud/vision');
const db = require('./db');

const client = new ImageAnnotatorClient();

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

// Recognize a face and return the associated student ID
async function recognizeFace(image) {
    try {
        const students = await getStudents(); // Fetch all students from Firestore

        for (const student of students) {
            const isMatch = await compareWithCloud(student.faceData, image); // Compare face using cloud
            if (isMatch) {
                console.log(`Face matched with student ID: ${student.studentId}`);
                return student.studentId; // Return the matched student ID
            }
        }

        console.log('No match found for the input face');
        return null;
    } catch (error) {
        console.error('Error recognizing face:', error);
        throw new Error('Failed to recognize face');
    }
}

// Compare two face images using Google Vision API
async function compareWithCloud(baseImage, inputImage) {
    try {
        const [result] = await client.similarImages({
            requests: [
                {
                    image: { content: baseImage.split(',')[1] }, // Base student face data
                    features: [{ type: 'FACE_DETECTION' }],
                },
                {
                    image: { content: inputImage.split(',')[1] }, // Input image for recognition
                    features: [{ type: 'FACE_DETECTION' }],
                },
            ],
        });

        if (result.responses && result.responses.length > 0) {
            const similarityScore = result.responses[0].faceAnnotations[0].detectionConfidence || 0;
            return similarityScore > 0.8; // Match if confidence is greater than 80%
        }

        return false;
    } catch (error) {
        console.error('Error with Google Vision API for comparison:', error);
        throw new Error('Google Vision API comparison failed');
    }
}

// Fetch all students from Firestore
async function getStudents() {
    try {
        const students = await db.collection('students').get();
        return students.docs.map(doc => ({
            studentId: doc.id,
            faceData: doc.data().faceData,
        }));
    } catch (error) {
        console.error('Error fetching students from Firestore:', error);
        throw new Error('Failed to fetch students');
    }
}

module.exports = { detectFaces, recognizeFace };