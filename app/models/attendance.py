"""Attendance model for managing attendance records"""

from datetime import datetime, time, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.hybrid import hybrid_property
from app import db
from app.constants import AttendanceStatus, DefaultValue

class Attendance(db.Model):
    """Attendance model for tracking student attendance"""
    __tablename__ = 'attendance'
    
    # Basic fields
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_in = db.Column(db.Time)
    time_out = db.Column(db.Time)
    status = db.Column(db.String(20), nullable=False, default=AttendanceStatus.ABSENT.value)
    
    # Additional information
    remarks = db.Column(db.Text)
    location = db.Column(db.String(255))  # Location where attendance was marked
    marked_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # User who marked the attendance
    verification_method = db.Column(db.String(50))  # Method used to verify attendance (face, manual, etc.)
    verification_data = db.Column(db.JSON)  # Additional verification data (confidence score, etc.)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super(Attendance, self).__init__(**kwargs)
        if not self.verification_data:
            self.verification_data = {}
    
    @hybrid_property
    def is_present(self) -> bool:
        """Check if student is marked as present"""
        return self.status == AttendanceStatus.PRESENT.value
    
    @hybrid_property
    def is_late(self) -> bool:
        """Check if student is marked as late"""
        return self.status == AttendanceStatus.LATE.value
    
    @hybrid_property
    def is_absent(self) -> bool:
        """Check if student is marked as absent"""
        return self.status == AttendanceStatus.ABSENT.value
    
    @hybrid_property
    def is_excused(self) -> bool:
        """Check if student is marked as excused"""
        return self.status == AttendanceStatus.EXCUSED.value
    
    @hybrid_property
    def duration(self) -> Optional[timedelta]:
        """Calculate attendance duration"""
        if self.time_in and self.time_out:
            time_in = datetime.combine(self.date, self.time_in)
            time_out = datetime.combine(self.date, self.time_out)
            return time_out - time_in
        return None
    
    def mark_attendance(self, time_in: time, verification_method: str,
                       verification_data: Dict[str, Any] = None) -> None:
        """Mark attendance with time and verification data"""
        from app.models.subject import Subject
        
        self.time_in = time_in
        self.verification_method = verification_method
        self.verification_data = verification_data or {}
        
        # Get subject schedule for the day
        subject = Subject.query.get(self.subject_id)
        if subject:
            day_schedule = subject.get_schedule_for_day(self.date.strftime('%A'))
            if day_schedule:
                scheduled_time = datetime.strptime(day_schedule[0], '%H:%M').time()
                time_diff = datetime.combine(self.date, time_in) - \
                           datetime.combine(self.date, scheduled_time)
                
                # Determine status based on arrival time
                if time_diff.total_seconds() <= 0:
                    self.status = AttendanceStatus.PRESENT.value
                elif time_diff.total_seconds() <= DefaultValue.LATE_THRESHOLD:
                    self.status = AttendanceStatus.LATE.value
                else:
                    self.status = AttendanceStatus.ABSENT.value
        
        db.session.commit()
    
    def mark_exit(self, time_out: time) -> None:
        """Mark exit time"""
        self.time_out = time_out
        db.session.commit()
    
    def excuse_absence(self, remarks: str, marked_by: int) -> None:
        """Mark attendance as excused"""
        self.status = AttendanceStatus.EXCUSED.value
        self.remarks = remarks
        self.marked_by = marked_by
        db.session.commit()
    
    @classmethod
    def get_student_attendance(cls, student_id: int, subject_id: Optional[int] = None,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None) -> List['Attendance']:
        """Get attendance records for a student"""
        query = cls.query.filter_by(student_id=student_id)
        
        if subject_id:
            query = query.filter_by(subject_id=subject_id)
        if start_date:
            query = query.filter(cls.date >= start_date.date())
        if end_date:
            query = query.filter(cls.date <= end_date.date())
        
        return query.order_by(cls.date.desc()).all()
    
    @classmethod
    def get_subject_attendance(cls, subject_id: int, date: Optional[datetime] = None,
                             status: Optional[str] = None) -> List['Attendance']:
        """Get attendance records for a subject"""
        query = cls.query.filter_by(subject_id=subject_id)
        
        if date:
            query = query.filter_by(date=date.date())
        if status:
            query = query.filter_by(status=status)
        
        return query.order_by(cls.date.desc(), cls.time_in.desc()).all()
    
    @classmethod
    def get_attendance_stats(cls, subject_id: int, start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get attendance statistics for a subject"""
        query = cls.query.filter_by(subject_id=subject_id)
        
        if start_date:
            query = query.filter(cls.date >= start_date.date())
        if end_date:
            query = query.filter(cls.date <= end_date.date())
        
        total = query.count()
        stats = {
            'total': total,
            'present': query.filter_by(status=AttendanceStatus.PRESENT.value).count(),
            'late': query.filter_by(status=AttendanceStatus.LATE.value).count(),
            'absent': query.filter_by(status=AttendanceStatus.ABSENT.value).count(),
            'excused': query.filter_by(status=AttendanceStatus.EXCUSED.value).count()
        }
        
        stats['attendance_rate'] = ((stats['present'] + stats['late']) / total * 100
                                  if total > 0 else 0)
        
        return stats
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert attendance record to dictionary"""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'subject_id': self.subject_id,
            'date': self.date.isoformat(),
            'time_in': self.time_in.strftime('%H:%M:%S') if self.time_in else None,
            'time_out': self.time_out.strftime('%H:%M:%S') if self.time_out else None,
            'status': self.status,
            'remarks': self.remarks,
            'location': self.location,
            'marked_by': self.marked_by,
            'verification_method': self.verification_method,
            'verification_data': self.verification_data,
            'duration': str(self.duration) if self.duration else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self) -> str:
        """String representation of attendance record"""
        return (f'<Attendance {self.student_id} - {self.subject_id} - '
                f'{self.date.isoformat()} - {self.status}>') 