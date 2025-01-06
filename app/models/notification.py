from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.hybrid import hybrid_property
from app import db
from app.constants import NotificationType

class Notification(db.Model):
    """Notification model for managing user notifications"""
    __tablename__ = 'notifications'
    
    # Basic fields
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    
    # Additional data
    data = db.Column(db.JSON)  # Additional context data
    icon = db.Column(db.String(50))  # Icon identifier
    link = db.Column(db.String(255))  # Related URL
    
    # Status
    is_read = db.Column(db.Boolean, default=False)
    is_sent = db.Column(db.Boolean, default=False)
    is_error = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text)
    
    # Delivery settings
    send_email = db.Column(db.Boolean, default=True)
    send_push = db.Column(db.Boolean, default=False)
    scheduled_for = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    sent_at = db.Column(db.DateTime)
    
    def __init__(self, **kwargs):
        super(Notification, self).__init__(**kwargs)
        if not self.data:
            self.data = {}
    
    @hybrid_property
    def is_scheduled(self) -> bool:
        """Check if notification is scheduled"""
        return bool(self.scheduled_for and self.scheduled_for > datetime.utcnow())
    
    @hybrid_property
    def is_pending(self) -> bool:
        """Check if notification is pending delivery"""
        return not self.is_sent and not self.is_error
    
    @hybrid_property
    def is_actionable(self) -> bool:
        """Check if notification has an action link"""
        return bool(self.link)
    
    def mark_as_read(self) -> None:
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
            db.session.commit()
    
    def mark_as_unread(self) -> None:
        """Mark notification as unread"""
        if self.is_read:
            self.is_read = False
            self.read_at = None
            db.session.commit()
    
    def mark_as_sent(self, error: Optional[str] = None) -> None:
        """Mark notification as sent"""
        self.is_sent = True
        self.sent_at = datetime.utcnow()
        if error:
            self.is_error = True
            self.error_message = error
        db.session.commit()
    
    def reschedule(self, scheduled_for: datetime) -> None:
        """Reschedule notification"""
        if scheduled_for > datetime.utcnow():
            self.scheduled_for = scheduled_for
            self.is_sent = False
            self.is_error = False
            self.error_message = None
            self.sent_at = None
            db.session.commit()
    
    @classmethod
    def create_attendance_notification(cls, student_id: int, subject_id: int,
                                    status: str) -> 'Notification':
        """Create attendance notification"""
        from app.models.user import User
        from app.models.subject import Subject
        
        student = User.query.get(student_id)
        subject = Subject.query.get(subject_id)
        
        if not student or not subject:
            return None
        
        notification = cls(
            recipient_id=student_id,
            type=NotificationType.ATTENDANCE.value,
            title=f"Attendance Marked - {subject.name}",
            message=f"Your attendance has been marked as {status} for {subject.name}",
            data={
                'subject_id': subject_id,
                'subject_name': subject.name,
                'status': status,
                'date': datetime.utcnow().strftime('%Y-%m-%d')
            },
            icon='calendar-check',
            link=f"/attendance/view/{subject_id}"
        )
        
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @classmethod
    def create_subject_notification(cls, teacher_id: int, subject_id: int,
                                  action: str) -> 'Notification':
        """Create subject-related notification"""
        from app.models.subject import Subject
        
        subject = Subject.query.get(subject_id)
        if not subject:
            return None
        
        notification = cls(
            recipient_id=teacher_id,
            type=NotificationType.SUBJECT.value,
            title=f"Subject {action} - {subject.name}",
            message=f"Subject {subject.name} has been {action}",
            data={
                'subject_id': subject_id,
                'subject_name': subject.name,
                'action': action
            },
            icon='book',
            link=f"/subjects/view/{subject_id}"
        )
        
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @classmethod
    def get_unread_count(cls, user_id: int) -> int:
        """Get count of unread notifications for user"""
        return cls.query.filter_by(
            recipient_id=user_id,
            is_read=False
        ).count()
    
    @classmethod
    def get_user_notifications(cls, user_id: int, page: int = 1,
                             per_page: int = 20) -> List['Notification']:
        """Get paginated list of user notifications"""
        return cls.query.filter_by(recipient_id=user_id)\
                   .order_by(cls.created_at.desc())\
                   .paginate(page=page, per_page=per_page, error_out=False)\
                   .items
    
    @classmethod
    def get_pending_notifications(cls) -> List['Notification']:
        """Get list of pending notifications"""
        now = datetime.utcnow()
        return cls.query.filter(
            (cls.is_sent == False) &
            (cls.is_error == False) &
            ((cls.scheduled_for == None) | (cls.scheduled_for <= now))
        ).all()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary"""
        return {
            'id': self.id,
            'recipient_id': self.recipient_id,
            'type': self.type,
            'title': self.title,
            'message': self.message,
            'data': self.data,
            'icon': self.icon,
            'link': self.link,
            'is_read': self.is_read,
            'is_sent': self.is_sent,
            'is_error': self.is_error,
            'error_message': self.error_message,
            'send_email': self.send_email,
            'send_push': self.send_push,
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None
        }
    
    def __repr__(self) -> str:
        """String representation of notification"""
        return f'<Notification {self.id}: {self.type} - {self.title}>' 