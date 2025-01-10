const express = require('express');
const router = express.Router();
const { firestore } = require('../firebase'); // Initialize Firestore
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');

const authenticate = async (req, res, next) => {
    const token = req.header('Authorization')?.replace('Bearer ', '');

    if (!token) {
        return res.status(401).json({ message: 'No token provided.' });
    }

    try {
        const decoded = jwt.verify(token, process.env.JWT_SECRET);
        const userDoc = await firestore.collection('users').doc(decoded.id).get();
        if (!userDoc.exists) {
            return res.status(401).json({ message: 'Invalid token.' });
        }

        req.user = { id: userDoc.id, ...userDoc.data() };
        next();
    } catch (error) {
        console.error('Authentication error:', error);
        res.status(401).json({ message: 'Invalid token.' });
    }
};

const authorize = (roles) => {
    return (req, res, next) => {
        if (!roles.includes(req.user.role)) {
            return res.status(403).json({ message: 'Access forbidden: insufficient rights.' });
        }
        next();
    };
};

// POST /api/admin/create-teacher
router.post('/create-teacher', async (req, res) => {
    const { email, password, classes } = req.body;

    try {
        // Check if user already exists
        const usersRef = firestore.collection('users');
        const userSnapshot = await usersRef.where('email', '==', email).get();
        if (!userSnapshot.empty) {
            return res.status(400).json({ message: 'User with this email already exists.' });
        }

        // Hash the password
        const hashedPassword = await bcrypt.hash(password, 10);

        // Create teacher account
        await usersRef.add({
            email,
            password: hashedPassword,
            role: 'teacher',
            class_assignments: classes,
            createdAt: new Date(),
        });

        res.status(201).json({ message: 'Teacher account created successfully.' });
    } catch (error) {
        console.error('Error creating teacher account:', error);
        res.status(500).json({ message: 'Server error.' });
    }
});

module.exports = router; 