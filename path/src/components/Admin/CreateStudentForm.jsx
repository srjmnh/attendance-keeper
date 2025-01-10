import React, { useState } from 'react';
import axios from 'axios';

function CreateStudentForm() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [studentID, setStudentID] = useState('');
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            await axios.post('/api/admin/create-student', { email, password, studentID });
            // Handle success (e.g., show a success message or reset form)
        } catch (err) {
            setError(err.response?.data?.message || 'An error occurred.');
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            <div>
                <label>Email:</label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div>
                <label>Password:</label>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            <div>
                <label>Student ID:</label>
                <input type="text" value={studentID} onChange={(e) => setStudentID(e.target.value)} required />
            </div>
            {error && <p className="error">{error}</p>}
            <button type="submit">Create Student Account</button>
        </form>
    );
}

export default CreateStudentForm; 