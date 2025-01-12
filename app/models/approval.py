from datetime import datetime
from enum import Enum
from typing import Dict, Any

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class ApprovalType(Enum):
    STUDENT_EDIT = "student_edit"
    ATTENDANCE_DISPUTE = "attendance_dispute"
    FACE_REGISTRATION = "face_registration"

class ApprovalRequest:
    def __init__(self, request_type: ApprovalType, requestor_id: str, data: Dict[str, Any]):
        self.id = None  # Will be set by Firestore
        self.type = request_type
        self.status = ApprovalStatus.PENDING
        self.requestor_id = requestor_id
        self.approver_id = None
        self.data = data
        self.created_at = datetime.utcnow()
        self.updated_at = self.created_at
        self.comments = []

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "status": self.status.value,
            "requestor_id": self.requestor_id,
            "approver_id": self.approver_id,
            "data": self.data,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "comments": self.comments
        }

    @staticmethod
    def from_dict(source: dict) -> 'ApprovalRequest':
        request = ApprovalRequest(
            ApprovalType(source["type"]),
            source["requestor_id"],
            source["data"]
        )
        request.status = ApprovalStatus(source["status"])
        request.approver_id = source.get("approver_id")
        request.created_at = source["created_at"]
        request.updated_at = source["updated_at"]
        request.comments = source.get("comments", [])
        return request 