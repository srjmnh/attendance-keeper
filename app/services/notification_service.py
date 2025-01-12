from typing import List, Optional
from datetime import datetime
from app.models.notification import Notification, NotificationType, NotificationPriority
from app.models.approval import ApprovalRequest
from google.cloud import firestore

class NotificationService:
    def __init__(self, db: firestore.Client):
        self.db = db
        self._notification_ref = self.db.collection('notifications')

    async def create_notification(self, notification: Notification) -> str:
        """Create a new notification."""
        doc_ref = self._notification_ref.document()
        notification.id = doc_ref.id
        await doc_ref.set(notification.to_dict())
        return doc_ref.id

    async def get_user_notifications(self, user_id: str, limit: int = 50) -> List[Notification]:
        """Get notifications for a specific user."""
        docs = await self._notification_ref.where('user_id', '==', user_id)\
            .where('status', '!=', 'archived')\
            .order_by('created_at', direction=firestore.Query.DESCENDING)\
            .limit(limit)\
            .get()
        return [Notification.from_dict(doc.to_dict()) for doc in docs]

    async def mark_as_read(self, notification_id: str) -> None:
        """Mark a notification as read."""
        await self._notification_ref.document(notification_id).update({
            'status': 'read',
            'read_at': datetime.utcnow()
        })

    async def archive_notification(self, notification_id: str) -> None:
        """Archive a notification."""
        await self._notification_ref.document(notification_id).update({
            'status': 'archived'
        })

    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications for a user."""
        docs = await self._notification_ref.where('user_id', '==', user_id)\
            .where('status', '==', 'unread')\
            .get()
        return len(docs)

    # Specific notification creators
    async def notify_attendance_marked(self, student_id: str, class_info: dict) -> None:
        """Notify a student that their attendance was marked."""
        notification = Notification(
            NotificationType.ATTENDANCE_MARKED,
            student_id,
            "Attendance Marked",
            f"Your attendance for {class_info['subject']} has been marked.",
            NotificationPriority.NORMAL,
            class_info
        )
        notification.add_action(
            "View Attendance",
            f"/attendance/view?date={class_info['date']}"
        )
        await self.create_notification(notification)

    async def notify_admins_new_approval(self, request: ApprovalRequest) -> None:
        """Notify admins about a new approval request."""
        # Get admin user IDs from your user service
        admin_ids = await self._get_admin_ids()
        
        for admin_id in admin_ids:
            notification = Notification(
                NotificationType.APPROVAL_REQUIRED,
                admin_id,
                "New Approval Request",
                f"A new {request.type.value} request requires your approval.",
                NotificationPriority.HIGH,
                {"request_id": request.id}
            )
            notification.add_action(
                "Review Request",
                f"/admin/approvals/{request.id}"
            )
            await self.create_notification(notification)

    async def notify_request_approved(self, request: ApprovalRequest) -> None:
        """Notify requestor that their request was approved."""
        notification = Notification(
            NotificationType.APPROVAL_RESOLVED,
            request.requestor_id,
            "Request Approved",
            f"Your {request.type.value} request has been approved.",
            NotificationPriority.NORMAL,
            {"request_id": request.id}
        )
        notification.add_action(
            "View Details",
            f"/approvals/{request.id}"
        )
        await self.create_notification(notification)

    async def notify_request_rejected(self, request: ApprovalRequest) -> None:
        """Notify requestor that their request was rejected."""
        notification = Notification(
            NotificationType.APPROVAL_RESOLVED,
            request.requestor_id,
            "Request Rejected",
            f"Your {request.type.value} request has been rejected.",
            NotificationPriority.HIGH,
            {"request_id": request.id}
        )
        notification.add_action(
            "View Details",
            f"/approvals/{request.id}"
        )
        await self.create_notification(notification)

    async def notify_dispute_filed(self, dispute_id: str, teacher_id: str, student_info: dict) -> None:
        """Notify teacher about an attendance dispute."""
        notification = Notification(
            NotificationType.DISPUTE_FILED,
            teacher_id,
            "New Attendance Dispute",
            f"Student {student_info['name']} has filed an attendance dispute.",
            NotificationPriority.HIGH,
            {"dispute_id": dispute_id, "student": student_info}
        )
        notification.add_action(
            "Review Dispute",
            f"/disputes/{dispute_id}"
        )
        await self.create_notification(notification)

    async def _get_admin_ids(self) -> List[str]:
        """Get list of admin user IDs."""
        # Implement this based on your user management system
        admin_docs = await self.db.collection('users')\
            .where('role', '==', 'admin')\
            .get()
        return [doc.id for doc in admin_docs] 