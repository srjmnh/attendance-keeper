const db = require('./db');

// Fetch all subjects
async function getSubjects(req, res) {
    try {
        const subjectsSnapshot = await db.collection('subjects').get();
        const subjects = subjectsSnapshot.docs.map(doc => ({
            id: doc.id,
            ...doc.data(),
        }));

        res.json({ success: true, subjects });
    } catch (error) {
        console.error('Error fetching subjects:', error);
        res.status(500).json({ success: false, message: 'Failed to fetch subjects' });
    }
}

// Add a new subject
async function addSubject(req, res) {
    const { subjectName } = req.body;

    try {
        if (!subjectName) {
            return res.status(400).json({ success: false, message: 'Subject name is required' });
        }

        await db.collection('subjects').add({ name: subjectName });
        res.json({ success: true, message: 'Subject added successfully' });
    } catch (error) {
        console.error('Error adding subject:', error);
        res.status(500).json({ success: false, message: 'Failed to add subject' });
    }
}

module.exports = { getSubjects, addSubject };