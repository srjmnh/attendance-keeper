from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.ext.hybrid import hybrid_property
from app import db

class Department(db.Model):
    """Department model for managing academic departments"""
    __tablename__ = 'departments'
    
    # Basic fields
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Contact information
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    location = db.Column(db.String(255))
    website = db.Column(db.String(255))
    
    # Department head
    head_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    head_since = db.Column(db.Date)
    
    # Status and configuration
    is_active = db.Column(db.Boolean, default=True)
    max_subjects = db.Column(db.Integer)  # Maximum subjects allowed per semester
    max_students = db.Column(db.Integer)  # Maximum students allowed in department
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    subjects = db.relationship('Subject', backref='department', lazy='dynamic')
    users = db.relationship('User', backref='department', lazy='dynamic',
                          foreign_keys='User.department_id')
    head = db.relationship('User', backref='headed_department', uselist=False,
                         foreign_keys=[head_id])
    
    def __init__(self, **kwargs):
        super(Department, self).__init__(**kwargs)
        if not self.code:
            # Generate code from name if not provided
            self.code = ''.join(word[0].upper() for word in self.name.split()[:3])
    
    @hybrid_property
    def student_count(self) -> int:
        """Get number of students in department"""
        return self.users.filter_by(role='student').count()
    
    @hybrid_property
    def teacher_count(self) -> int:
        """Get number of teachers in department"""
        return self.users.filter_by(role='teacher').count()
    
    @hybrid_property
    def subject_count(self) -> int:
        """Get number of subjects in department"""
        return self.subjects.count()
    
    def get_students(self, active_only: bool = True) -> List['User']:
        """Get list of students in department"""
        query = self.users.filter_by(role='student')
        if active_only:
            query = query.filter_by(status='active')
        return query.all()
    
    def get_teachers(self, active_only: bool = True) -> List['User']:
        """Get list of teachers in department"""
        query = self.users.filter_by(role='teacher')
        if active_only:
            query = query.filter_by(status='active')
        return query.all()
    
    def get_subjects(self, active_only: bool = True,
                    semester: str = None) -> List['Subject']:
        """Get list of subjects in department"""
        query = self.subjects
        if active_only:
            query = query.filter_by(status='active')
        if semester:
            query = query.filter_by(semester=semester)
        return query.all()
    
    def get_attendance_stats(self, start_date: datetime = None,
                           end_date: datetime = None) -> Dict[str, Any]:
        """Get attendance statistics for department"""
        from app.models.attendance import Attendance
        
        # Get all subjects in department
        subject_ids = [subject.id for subject in self.subjects]
        
        # Base query for attendance records
        query = Attendance.query.filter(Attendance.subject_id.in_(subject_ids))
        
        if start_date:
            query = query.filter(Attendance.date >= start_date.date())
        if end_date:
            query = query.filter(Attendance.date <= end_date.date())
        
        total = query.count()
        stats = {
            'total_records': total,
            'present': query.filter_by(status='present').count(),
            'late': query.filter_by(status='late').count(),
            'absent': query.filter_by(status='absent').count(),
            'excused': query.filter_by(status='excused').count()
        }
        
        stats['attendance_rate'] = ((stats['present'] + stats['late']) / total * 100
                                  if total > 0 else 0)
        
        return stats
    
    def can_add_subject(self) -> bool:
        """Check if department can add more subjects"""
        if not self.max_subjects:
            return True
        return self.subject_count < self.max_subjects
    
    def can_add_student(self) -> bool:
        """Check if department can add more students"""
        if not self.max_students:
            return True
        return self.student_count < self.max_students
    
    def assign_head(self, user_id: int) -> bool:
        """Assign department head"""
        from app.models.user import User
        
        user = User.query.get(user_id)
        if user and user.role in ['teacher', 'admin']:
            self.head_id = user.id
            self.head_since = datetime.utcnow().date()
            db.session.commit()
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert department to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'email': self.email,
            'phone': self.phone,
            'location': self.location,
            'website': self.website,
            'head_id': self.head_id,
            'head_name': self.head.full_name if self.head else None,
            'head_since': self.head_since.isoformat() if self.head_since else None,
            'is_active': self.is_active,
            'max_subjects': self.max_subjects,
            'max_students': self.max_students,
            'student_count': self.student_count,
            'teacher_count': self.teacher_count,
            'subject_count': self.subject_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self) -> str:
        """String representation of department"""
        return f'<Department {self.code}: {self.name}>' 