from datetime import datetime

class Attendance:
    """Attendance model for managing student attendance records"""

    def __init__(self, attendance_data):
        """Initialize attendance with data from database"""
        self.id = attendance_data.get('id')
        self.student_id = attendance_data.get('student_id')
        self.subject_id = attendance_data.get('subject_id')
        self.date = attendance_data.get('date')
        if isinstance(self.date, str):
            self.date = datetime.fromisoformat(self.date)
        self.status = attendance_data.get('status', 'present')  # present, absent, late
        self.marked_by = attendance_data.get('marked_by')  # teacher_id
        self.confidence_score = attendance_data.get('confidence_score')  # face recognition confidence
        self.verification_method = attendance_data.get('verification_method', 'face')  # face, manual
        self.notes = attendance_data.get('notes')

    def to_dict(self):
        """Convert attendance object to dictionary"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'subject_id': self.subject_id,
            'date': self.date.isoformat() if self.date else None,
            'status': self.status,
            'marked_by': self.marked_by,
            'confidence_score': self.confidence_score,
            'verification_method': self.verification_method,
            'notes': self.notes
        }

    @staticmethod
    def from_dict(attendance_dict):
        """Create attendance object from dictionary"""
        return Attendance(attendance_dict)

    def update(self, data):
        """Update attendance attributes"""
        if 'student_id' in data:
            self.student_id = data['student_id']
        if 'subject_id' in data:
            self.subject_id = data['subject_id']
        if 'date' in data:
            self.date = data['date']
            if isinstance(self.date, str):
                self.date = datetime.fromisoformat(self.date)
        if 'status' in data:
            self.status = data['status']
        if 'marked_by' in data:
            self.marked_by = data['marked_by']
        if 'confidence_score' in data:
            self.confidence_score = data['confidence_score']
        if 'verification_method' in data:
            self.verification_method = data['verification_method']
        if 'notes' in data:
            self.notes = data['notes']

    def is_present(self):
        """Check if attendance status is present"""
        return self.status == 'present'

    def is_absent(self):
        """Check if attendance status is absent"""
        return self.status == 'absent'

    def is_late(self):
        """Check if attendance status is late"""
        return self.status == 'late'

    def is_verified_by_face(self):
        """Check if attendance was verified by face recognition"""
        return self.verification_method == 'face'

    def get_formatted_date(self, format='%Y-%m-%d %H:%M'):
        """Get formatted date string"""
        return self.date.strftime(format) if self.date else None

    def __str__(self):
        """String representation of attendance"""
        return f"Attendance: {self.student_id} - {self.get_formatted_date()} ({self.status})" 