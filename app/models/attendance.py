from firebase_admin import firestore
from datetime import datetime

db = firestore.client()

class Attendance:
    def __init__(self, id=None, student_id=None, name=None, subject_id=None, 
                 subject_name=None, timestamp=None, status="PRESENT", confidence=None,
                 location=None, verified_by=None):
        self.id = id
        self.student_id = student_id
        self.name = name
        self.subject_id = subject_id
        self.subject_name = subject_name
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.status = status
        self.confidence = confidence  # Face recognition confidence
        self.location = location or {}  # Optional location data
        self.verified_by = verified_by  # Teacher/admin who verified

    def to_dict(self):
        return {
            'student_id': self.student_id,
            'name': self.name,
            'subject_id': self.subject_id,
            'subject_name': self.subject_name,
            'timestamp': self.timestamp,
            'status': self.status,
            'confidence': self.confidence,
            'location': self.location,
            'verified_by': self.verified_by,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

    @staticmethod
    def from_dict(id, data):
        return Attendance(
            id=id,
            student_id=data.get('student_id'),
            name=data.get('name'),
            subject_id=data.get('subject_id'),
            subject_name=data.get('subject_name'),
            timestamp=data.get('timestamp'),
            status=data.get('status', 'PRESENT'),
            confidence=data.get('confidence'),
            location=data.get('location', {}),
            verified_by=data.get('verified_by')
        )

    def save(self):
        """Save attendance record to Firestore"""
        if not self.id:
            # New attendance record
            doc_ref = db.collection('attendance').document()
            self.id = doc_ref.id
        else:
            # Existing attendance record
            doc_ref = db.collection('attendance').document(self.id)
        
        doc_ref.set(self.to_dict(), merge=True)
        return self

    @staticmethod
    def get_by_id(attendance_id):
        """Get attendance record by ID"""
        doc = db.collection('attendance').document(attendance_id).get()
        if not doc.exists:
            return None
        return Attendance.from_dict(doc.id, doc.to_dict())

    @staticmethod
    def get_by_student(student_id, start_date=None, end_date=None, subject_id=None):
        """Get attendance records for a student"""
        query = db.collection('attendance').where('student_id', '==', student_id)
        
        if start_date:
            query = query.where('timestamp', '>=', start_date.isoformat())
        if end_date:
            query = query.where('timestamp', '<=', end_date.isoformat())
        if subject_id:
            query = query.where('subject_id', '==', subject_id)

        records = []
        for doc in query.stream():
            records.append(Attendance.from_dict(doc.id, doc.to_dict()))
        return records

    @staticmethod
    def get_by_subject(subject_id, start_date=None, end_date=None):
        """Get attendance records for a subject"""
        query = db.collection('attendance').where('subject_id', '==', subject_id)
        
        if start_date:
            query = query.where('timestamp', '>=', start_date.isoformat())
        if end_date:
            query = query.where('timestamp', '<=', end_date.isoformat())

        records = []
        for doc in query.stream():
            records.append(Attendance.from_dict(doc.id, doc.to_dict()))
        return records

    @staticmethod
    def mark_attendance_from_recognition(recognition_result, subject_id=None, subject_name=None, verified_by=None):
        """Create attendance records from face recognition results"""
        records = []
        for person in recognition_result.get('identified_people', []):
            if 'student_id' in person and 'name' in person:  # Only mark for identified faces
                attendance = Attendance(
                    student_id=person['student_id'],
                    name=person['name'],
                    subject_id=subject_id,
                    subject_name=subject_name,
                    confidence=person.get('confidence'),
                    verified_by=verified_by
                )
                attendance.save()
                records.append(attendance)
        return records

    def verify(self, verified_by):
        """Verify attendance record by teacher/admin"""
        self.verified_by = verified_by
        self.save()
        return self

    def update_status(self, status, verified_by=None):
        """Update attendance status"""
        self.status = status
        if verified_by:
            self.verified_by = verified_by
        self.save()
        return self 