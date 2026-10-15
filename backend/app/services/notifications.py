
from sqlalchemy.orm import Session

from app.models import Notification


VALID_NOTIFICATION_TYPES = {
    "EVENT",
    "BOOKING",
    "PAYMENT",
    "SYSTEM",
}


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "SYSTEM",
) -> Notification:
    notification_type = notification_type.upper()

    if notification_type not in VALID_NOTIFICATION_TYPES:
        raise ValueError("Invalid notification type.")

    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        is_read=False,
    )

    db.add(notification)
    db.flush()

    return notification
