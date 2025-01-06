from datetime import datetime

class Subject:
    def __init__(self, id=None, name=None, code=None, teacher_id=None, 
                 class_name=None, division=None, description=None):
        self.id = id
        self.name = name
        self.code = code
        self.teacher_id = teacher_id
        self.class_name = class_name
        self.division = division
        self.description = description
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'teacher_id': self.teacher_id,
            'class_name': self.class_name,
            'division': self.division,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @staticmethod
    def from_dict(data):
        subject = Subject()
        for field in ['id', 'name', 'code', 'teacher_id', 'class_name', 
                     'division', 'description']:
            if field in data:
                setattr(subject, field, data[field])
        if 'created_at' in data:
            subject.created_at = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data:
            subject.updated_at = datetime.fromisoformat(data['updated_at'])
        return subject

    def __repr__(self):
        return f'<Subject {self.code}: {self.name}>' 