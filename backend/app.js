require('dotenv').config();
const express = require('express');
const path = require('path');
const bodyParser = require('body-parser');
const fetch = require('node-fetch');
const { saveAttendance } = require('./firebase');
const { registerFace } = require('./face-training');

const app = express();
app.use(bodyParser.json());

// Serve static files from the frontend folder
const frontendPath = path.join(__dirname, '../frontend');
app.use(express.static(frontendPath));

// Root route to serve the frontend
app.get('/', (req, res) => {
  res.sendFile(path.join(frontendPath, 'index.html'));
});

// Recognize Face
const VISION_API_URL = `https://vision.googleapis.com/v1/images:annotate?key=${process.env.VISION_API_KEY}`;
app.post('/recognize', async (req, res) => {
  try {
    const { image } = req.body;
    const response = await fetch(VISION_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        requests: [
          {
            image: { content: image.split(',')[1] },
            features: [{ type: 'FACE_DETECTION' }]
          }
        ]
      })
    });
    const result = await response.json();
    const faces = result.responses[0].faceAnnotations;
    if (faces && faces.length > 0) {
      const studentName = 'Detected Face'; // Logic to match with database
      const timestamp = new Date().toISOString();
      await saveAttendance(studentName, timestamp);
      res.json({ success: true, studentName });
    } else {
      res.json({ success: false, message: 'No face detected' });
    }
  } catch (error) {
    console.error('Error processing request:', error);
    res.status(500).json({ success: false, message: 'Internal server error' });
  }
});

// Register Face
app.post('/register', async (req, res) => {
  const { studentName, studentId, image } = req.body;
  const result = await registerFace(studentName, studentId, image);
  res.json(result);
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Backend server running on port ${PORT}`);
});