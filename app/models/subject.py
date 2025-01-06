from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.ext.hybrid import hybrid_property
from app import db
from app.constants import SubjectStatus

class Subject(db.Model):
    """Subject model for storing course information"""
    __tablename__ = 'subjects'
    
    # Basic fields
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    credits = db.Column(db.Integer, default=3)
    status = db.Column(db.String(20), nullable=False, default=SubjectStatus.ACTIVE.value)
    
    # Schedule and capacity
    schedule = db.Column(db.JSON)  # Format: {"day": ["start_time", "end_time"]}
    classroom = db.Column(db.String(50))
    capacity = db.Column(db.Integer)
    enrolled_count = db.Column(db.Integer, default=0)
    
    # Academic information
    department = db.Column(db.String(100))
    semester = db.Column(db.String(20))
    academic_year = db.Column(db.String(9))  # Format: "2023-2024"
    prerequisites = db.Column(db.JSON)  # List of subject codes
    
    # Relationships
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    attendances = db.relationship('Attendance', backref='subject', lazy='dynamic',
                                cascade='all, delete-orphan')
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super(Subject, self).__init__(**kwargs)
        if not self.schedule:
            self.schedule = {}
        if not self.prerequisites:
            self.prerequisites = []
    
    @hybrid_property
    def is_active(self) -> bool:
        """Check if subject is active"""
        return self.status == SubjectStatus.ACTIVE.value
    
    @hybrid_property
    def is_full(self) -> bool:
        """Check if subject has reached capacity"""
        return self.capacity and self.enrolled_count >= self.capacity
    
    @hybrid_property
    def available_seats(self) -> int:
        """Get number of available seats"""
        if not self.capacity:
            return float('inf')
        return max(0, self.capacity - self.enrolled_count)
    
    def get_schedule_for_day(self, day: str) -> List[str]:
        """Get schedule for specific day"""
        return self.schedule.get(day.lower(), [])
    
    def update_enrolled_count(self) -> None:
        """Update enrolled student count"""
        from app.models.enrollment import Enrollment
        self.enrolled_count = Enrollment.query.filter_by(
            subject_id=self.id,
            status='active'
        ).count()
        db.session.commit()
    
    def get_attendance_stats(self, start_date: datetime = None,
                           end_date: datetime = None) -> Dict[str, Any]:
        """Get attendance statistics for the subject"""
        from app.models.attendance import Attendance
        
        query = Attendance.query.filter_by(subject_id=self.id)
        
        if start_date:
            query = query.filter(Attendance.date >= start_date)
        if end_date:
            query = query.filter(Attendance.date <= end_date)
        
        total = query.count()
        present = query.filter_by(status='present').count()
        absent = query.filter_by(status='absent').count()
        late = query.filter_by(status='late').count()
        excused = query.filter_by(status='excused').count()
        
        return {
            'total': total,
            'present': present,
            'absent': absent,
            'late': late,
            'excused': excused,
            'attendance_rate': (present + late) / total * 100 if total > 0 else 0
        }
    
    def get_student_list(self) -> List[Dict[str, Any]]:
        """Get list of enrolled students with their attendance records"""
        from app.models.enrollment import Enrollment
        from app.models.user import User
        from app.models.attendance import Attendance
        
        students = []
        enrollments = Enrollment.query.filter_by(
            subject_id=self.id,
            status='active'
        ).all()
        
        for enrollment in enrollments:
            student = User.query.get(enrollment.student_id)
            if student:
                attendance_records = Attendance.query.filter_by(
                    subject_id=self.id,
                    student_id=student.id
                ).all()
                
                total = len(attendance_records)
                present = sum(1 for a in attendance_records if a.status == 'present')
                late = sum(1 for a in attendance_records if a.status == 'late')
                
                students.append({
                    'student_id': student.id,
                    'student_name': student.full_name,
                    'email': student.email,
                    'attendance_rate': (present + late) / total * 100 if total > 0 else 0,
                    'total_classes': total,
                    'present': present,
                    'late': late,
                    'enrollment_date': enrollment.created_at.strftime('%Y-%m-%d')
                })
        
        return students
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert subject to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'credits': self.credits,
            'status': self.status,
            'schedule': self.schedule,
            'classroom': self.classroom,
            'capacity': self.capacity,
            'enrolled_count': self.enrolled_count,
            'available_seats': self.available_seats,
            'department': self.department,
            'semester': self.semester,
            'academic_year': self.academic_year,
            'prerequisites': self.prerequisites,
            'teacher_id': self.teacher_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self) -> str:
        """String representation of subject"""
        return f'<Subject {self.code}: {self.name}>' 