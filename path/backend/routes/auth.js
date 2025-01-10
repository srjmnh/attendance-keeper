const express = require('express');
const router = express.Router();
const { firestore } = require('../firebase');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
require('dotenv').config();

// POST /api/auth/login
router.post('/login', async (req, res) => {
    const { email, password } = req.body;

    try {
        const usersRef = firestore.collection('users');
        const userSnapshot = await usersRef.where('email', '==', email).limit(1).get();

        if (userSnapshot.empty) {
            return res.status(400).json({ message: 'Invalid credentials.' });
        }

        const user = userSnapshot.docs[0];
        const userData = user.data();

        const isMatch = await bcrypt.compare(password, userData.password);
        if (!isMatch) {
            return res.status(400).json({ message: 'Invalid credentials.' });
        }

        // Generate JWT using SECRET_KEY
        const token = jwt.sign({ id: user.id }, process.env.SECRET_KEY, { expiresIn: '1h' });

        res.json({ token, role: userData.role });
    } catch (error) {
        console.error('Error during login:', error);
        res.status(500).json({ message: 'Server error.' });
    }
});

module.exports = router; 