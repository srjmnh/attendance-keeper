import React, { useState, useEffect } from 'react';
import axios from 'axios';

function CreateTeacherForm() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [classes, setClasses] = useState([]);
    const [selectedClasses, setSelectedClasses] = useState([]);
    const [error, setError] = useState('');

    useEffect(() => {
        // Fetch available classes from the backend
        axios.get('/api/classes')
            .then(response => setClasses(response.data.classes))
            .catch(err => console.error('Error fetching classes:', err));
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            await axios.post('/api/admin/create-teacher', { email, password, classes: selectedClasses });
            // Handle success
        } catch (err) {
            setError(err.response?.data?.message || 'An error occurred.');
        }
    };

    const handleClassSelection = (e) => {
        const value = e.target.value;
        setSelectedClasses(prev =>
            prev.includes(value) ? prev.filter(cls => cls !== value) : [...prev, value]
        );
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
                <label>Assign Classes:</label>
                {classes.map(cls => (
                    <div key={cls.id}>
                        <input
                            type="checkbox"
                            value={cls.id}
                            checked={selectedClasses.includes(cls.id)}
                            onChange={handleClassSelection}
                        />
                        <span>{cls.name}</span>
                    </div>
                ))}
            </div>
            {error && <p className="error">{error}</p>}
            <button type="submit">Create Teacher Account</button>
        </form>
    );
}

export default CreateTeacherForm; 