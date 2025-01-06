from datetime import datetime

class Attendance:
    def __init__(self, id=None, student_id=None, subject_id=None, 
                 date=None, status='present', confidence=None, 
                 image_url=None, marked_by=None):
        self.id = id
        self.student_id = student_id
        self.subject_id = subject_id
        self.date = date or datetime.utcnow()
        self.status = status
        self.confidence = confidence
        self.image_url = image_url
        self.marked_by = marked_by
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'subject_id': self.subject_id,
            'date': self.date.isoformat() if self.date else None,
            'status': self.status,
            'confidence': self.confidence,
            'image_url': self.image_url,
            'marked_by': self.marked_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def from_dict(data):
        attendance = Attendance()
        for field in ['id', 'student_id', 'subject_id', 'status', 
                     'confidence', 'image_url', 'marked_by']:
            if field in data:
                setattr(attendance, field, data[field])
        if 'date' in data:
            attendance.date = datetime.fromisoformat(data['date'])
        if 'created_at' in data:
            attendance.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            attendance.updated_at = datetime.fromisoformat(data['updated_at'])
        return attendance

    def __repr__(self):
        return f'<Attendance {self.student_id} - {self.subject_id} - {self.date}>' 