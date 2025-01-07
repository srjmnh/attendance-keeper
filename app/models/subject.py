from datetime import datetime

class Subject:
    """Subject model for managing course subjects"""

    def __init__(self, subject_data):
        """Initialize subject with data from database"""
        self.id = subject_data.get('id')
        self.name = subject_data.get('name')
        self.description = subject_data.get('description')
        self.teacher_id = subject_data.get('teacher_id')
        self.class_name = subject_data.get('class_name')
        self.division = subject_data.get('division')

    def to_dict(self):
        """Convert subject object to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'teacher_id': self.teacher_id,
            'class_name': self.class_name,
            'division': self.division
        }

    @staticmethod
    def from_dict(subject_dict):
        """Create subject object from dictionary"""
        return Subject(subject_dict)

    def update(self, data):
        """Update subject attributes"""
        if 'name' in data:
            self.name = data['name']
        if 'description' in data:
            self.description = data['description']
        if 'teacher_id' in data:
            self.teacher_id = data['teacher_id']
        if 'class_name' in data:
            self.class_name = data['class_name']
        if 'division' in data:
            self.division = data['division']

    def get_class_info(self):
        """Get formatted class information"""
        return f"Class {self.class_name} - {self.division}"

    def __str__(self):
        """String representation of subject"""
        return f"{self.name} ({self.get_class_info()})" 