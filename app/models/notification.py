from datetime import datetime
from enum import Enum
from typing import Dict, Any, List

class NotificationType(Enum):
    ATTENDANCE_MARKED = "attendance_marked"
    DISPUTE_FILED = "dispute_filed"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RESOLVED = "approval_resolved"
    SYSTEM_ALERT = "system_alert"

class NotificationPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"

class NotificationStatus(Enum):
    UNREAD = "unread"
    READ = "read"
    ARCHIVED = "archived"

class Notification:
    def __init__(self, 
                 notification_type: NotificationType,
                 user_id: str,
                 title: str,
                 message: str,
                 priority: NotificationPriority = NotificationPriority.NORMAL,
                 data: Dict[str, Any] = None):
        self.id = None  # Will be set by Firestore
        self.type = notification_type
        self.user_id = user_id
        self.title = title
        self.message = message
        self.priority = priority
        self.status = NotificationStatus.UNREAD
        self.data = data or {}
        self.created_at = datetime.utcnow()
        self.read_at = None
        self.actions = []  # List of possible actions user can take

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.value,
            "status": self.status.value,
            "data": self.data,
            "created_at": self.created_at,
            "read_at": self.read_at,
            "actions": self.actions
        }

    @staticmethod
    def from_dict(source: dict) -> 'Notification':
        notification = Notification(
            NotificationType(source["type"]),
            source["user_id"],
            source["title"],
            source["message"],
            NotificationPriority(source["priority"]),
            source.get("data", {})
        )
        notification.status = NotificationStatus(source["status"])
        notification.created_at = source["created_at"]
        notification.read_at = source.get("read_at")
        notification.actions = source.get("actions", [])
        return notification

    def mark_as_read(self):
        self.status = NotificationStatus.READ
        self.read_at = datetime.utcnow()

    def archive(self):
        self.status = NotificationStatus.ARCHIVED

    def add_action(self, label: str, url: str, action_type: str = "link"):
        self.actions.append({
            "label": label,
            "url": url,
            "type": action_type
        }) 