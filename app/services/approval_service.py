from typing import List, Optional
from app.models.approval import ApprovalRequest, ApprovalStatus, ApprovalType
from app.services.notification_service import NotificationService
from google.cloud import firestore

class ApprovalService:
    def __init__(self, db: firestore.Client, notification_service: NotificationService):
        self.db = db
        self.notification_service = notification_service
        self._approval_ref = self.db.collection('approvals')

    async def create_request(self, request: ApprovalRequest) -> str:
        """Create a new approval request and notify relevant parties."""
        doc_ref = self._approval_ref.document()
        request.id = doc_ref.id
        await doc_ref.set(request.to_dict())

        # Notify admins about the new request
        await self.notification_service.notify_admins_new_approval(request)
        
        return doc_ref.id

    async def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request by ID."""
        doc = await self._approval_ref.document(request_id).get()
        return ApprovalRequest.from_dict(doc.to_dict()) if doc.exists else None

    async def get_pending_requests(self) -> List[ApprovalRequest]:
        """Get all pending approval requests."""
        docs = await self._approval_ref.where('status', '==', ApprovalStatus.PENDING.value).get()
        return [ApprovalRequest.from_dict(doc.to_dict()) for doc in docs]

    async def get_user_requests(self, user_id: str) -> List[ApprovalRequest]:
        """Get all requests made by a specific user."""
        docs = await self._approval_ref.where('requestor_id', '==', user_id).get()
        return [ApprovalRequest.from_dict(doc.to_dict()) for doc in docs]

    async def approve_request(self, request_id: str, approver_id: str, comment: str = None) -> None:
        """Approve a request and notify the requestor."""
        request = await self.get_request(request_id)
        if not request:
            raise ValueError("Request not found")

        request.status = ApprovalStatus.APPROVED
        request.approver_id = approver_id
        if comment:
            request.comments.append({
                "user_id": approver_id,
                "comment": comment,
                "timestamp": datetime.utcnow()
            })

        await self._approval_ref.document(request_id).update(request.to_dict())
        await self.notification_service.notify_request_approved(request)

    async def reject_request(self, request_id: str, approver_id: str, comment: str = None) -> None:
        """Reject a request and notify the requestor."""
        request = await self.get_request(request_id)
        if not request:
            raise ValueError("Request not found")

        request.status = ApprovalStatus.REJECTED
        request.approver_id = approver_id
        if comment:
            request.comments.append({
                "user_id": approver_id,
                "comment": comment,
                "timestamp": datetime.utcnow()
            })

        await self._approval_ref.document(request_id).update(request.to_dict())
        await self.notification_service.notify_request_rejected(request)

    async def add_comment(self, request_id: str, user_id: str, comment: str) -> None:
        """Add a comment to an approval request."""
        request = await self.get_request(request_id)
        if not request:
            raise ValueError("Request not found")

        request.comments.append({
            "user_id": user_id,
            "comment": comment,
            "timestamp": datetime.utcnow()
        })

        await self._approval_ref.document(request_id).update({
            "comments": request.comments
        }) 