from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.hybrid import hybrid_property
from app import db
from app.constants import ReportType, FileType

class Report(db.Model):
    """Report model for managing generated reports"""
    __tablename__ = 'reports'
    
    # Basic fields
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly, custom
    format = db.Column(db.String(10), nullable=False)  # pdf, excel, csv
    
    # Report parameters
    parameters = db.Column(db.JSON)  # Store report generation parameters
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    
    # File information
    file_path = db.Column(db.String(255))  # Path to stored report file
    file_size = db.Column(db.Integer)  # Size in bytes
    download_count = db.Column(db.Integer, default=0)
    
    # Relations
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    
    # Status
    is_generated = db.Column(db.Boolean, default=False)
    is_error = db.Column(db.Boolean, default=False)
    error_message = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    generated_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)  # Optional expiration date
    
    # Relationships
    creator = db.relationship('User', backref='reports', foreign_keys=[creator_id])
    department = db.relationship('Department', backref='reports')
    subject = db.relationship('Subject', backref='reports')
    
    def __init__(self, **kwargs):
        super(Report, self).__init__(**kwargs)
        if not self.parameters:
            self.parameters = {}
    
    @hybrid_property
    def is_expired(self) -> bool:
        """Check if report has expired"""
        return bool(self.expires_at and self.expires_at < datetime.utcnow())
    
    @hybrid_property
    def file_size_formatted(self) -> str:
        """Get formatted file size"""
        if not self.file_size:
            return '0 B'
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024
        return f"{self.file_size:.1f} TB"
    
    def mark_as_generated(self, file_path: str, file_size: int) -> None:
        """Mark report as generated"""
        self.is_generated = True
        self.is_error = False
        self.error_message = None
        self.file_path = file_path
        self.file_size = file_size
        self.generated_at = datetime.utcnow()
        db.session.commit()
    
    def mark_as_failed(self, error_message: str) -> None:
        """Mark report as failed"""
        self.is_generated = False
        self.is_error = True
        self.error_message = error_message
        db.session.commit()
    
    def increment_download_count(self) -> None:
        """Increment the download counter"""
        self.download_count += 1
        db.session.commit()
    
    def delete_file(self) -> bool:
        """Delete the report file"""
        if self.file_path:
            try:
                import os
                if os.path.exists(self.file_path):
                    os.remove(self.file_path)
                    self.file_path = None
                    self.file_size = None
                    self.is_generated = False
                    db.session.commit()
                    return True
            except Exception as e:
                from flask import current_app
                current_app.logger.error(f"Error deleting report file: {str(e)}")
        return False
    
    @classmethod
    def get_user_reports(cls, user_id: int, report_type: Optional[str] = None,
                        page: int = 1, per_page: int = 20) -> List['Report']:
        """Get paginated list of user's reports"""
        query = cls.query.filter_by(creator_id=user_id)
        
        if report_type:
            query = query.filter_by(type=report_type)
        
        return query.order_by(cls.created_at.desc())\
                   .paginate(page=page, per_page=per_page, error_out=False)\
                   .items
    
    @classmethod
    def get_department_reports(cls, department_id: int,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None) -> List['Report']:
        """Get department reports within date range"""
        query = cls.query.filter_by(department_id=department_id)
        
        if start_date:
            query = query.filter(cls.created_at >= start_date)
        if end_date:
            query = query.filter(cls.created_at <= end_date)
        
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_subject_reports(cls, subject_id: int,
                          report_type: Optional[str] = None) -> List['Report']:
        """Get reports for a specific subject"""
        query = cls.query.filter_by(subject_id=subject_id)
        
        if report_type:
            query = query.filter_by(type=report_type)
        
        return query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def cleanup_expired_reports(cls) -> int:
        """Delete expired reports and their files"""
        now = datetime.utcnow()
        expired_reports = cls.query.filter(
            cls.expires_at.isnot(None),
            cls.expires_at <= now
        ).all()
        
        deleted_count = 0
        for report in expired_reports:
            if report.delete_file():
                db.session.delete(report)
                deleted_count += 1
        
        if deleted_count:
            db.session.commit()
        
        return deleted_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'format': self.format,
            'parameters': self.parameters,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'file_size_formatted': self.file_size_formatted,
            'download_count': self.download_count,
            'creator_id': self.creator_id,
            'department_id': self.department_id,
            'subject_id': self.subject_id,
            'is_generated': self.is_generated,
            'is_error': self.is_error,
            'error_message': self.error_message,
            'is_expired': self.is_expired,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'generated_at': self.generated_at.isoformat() if self.generated_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
    
    def __repr__(self) -> str:
        """String representation of report"""
        return f'<Report {self.id}: {self.name} ({self.type})>' 