const db = require('./db');
const { detectFaces } = require('./azure-face');
const similarity = require('image-similarity'); // For similarity comparison
const Jimp = require('jimp'); // For image cropping

// Crop face using bounding box
async function cropFace(imageBase64, boundingBox) {
    const imageBuffer = Buffer.from(imageBase64, 'base64');
    const image = await Jimp.read(imageBuffer);

    const { left, top, width, height } = boundingBox;
    image.crop(left, top, width, height); // Crop face using bounding box

    const croppedBuffer = await image.getBufferAsync(Jimp.MIME_JPEG);
    return croppedBuffer.toString('base64'); // Return cropped face as base64
}

// Recognize a face using cropped image similarity
async function recognizeFace(req, res) {
    const { image } = req.body;

    try {
        const faces = await detectFaces(image); // Detect faces using Azure Face API
        if (faces.length === 0) {
            return res.status(400).json({ success: false, message: 'No face detected' });
        }

        const croppedFace = await cropFace(image, faces[0].faceRectangle);

        // Retrieve all students from Firebase
        const studentsSnapshot = await db.collection('students').get();
        const students = studentsSnapshot.docs.map(doc => ({
            id: doc.id,
            ...doc.data(),
        }));

        // Compare the cropped face with stored faces
        for (const student of students) {
            const similarityScore = await similarity.compareBase64(
                croppedFace,
                student.faceImage
            );

            if (similarityScore > 0.85) { // Example threshold for a match
                return res.json({
                    success: true,
                    message: 'Face recognized successfully',
                    student,
                });
            }
        }

        res.status(400).json({ success: false, message: 'Face not recognized' });
    } catch (error) {
        console.error('Error recognizing face:', error);
        res.status(500).json({ success: false, message: 'Error recognizing face' });
    }
}

module.exports = { recognizeFace };