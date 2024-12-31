const db = require('./db');

// Add a subject
async function addSubject(req, res) {
    const { subjectCode, subjectName } = req.body;
    try {
        const subjectDoc = db.collection('subjects').doc(subjectCode);
        await subjectDoc.set({ name: subjectName, code: subjectCode });
        res.json({ success: true, message: 'Subject added successfully' });
    } catch (error) {
        console.error('Error adding subject:', error);
        res.status(500).json({ success: false, message: 'Error adding subject' });
    }
}

// Get all subjects
async function getSubjects(req, res) {
    try {
        const snapshot = await db.collection('subjects').get();
        const subjects = snapshot.docs.map(doc => ({
            code: doc.id,
            name: doc.data().name,
        }));
        res.json(subjects);
    } catch (error) {
        console.error('Error fetching subjects:', error);
        res.status(500).json({ success: false, message: 'Error fetching subjects' });
    }
}

module.exports = { addSubject, getSubjects };