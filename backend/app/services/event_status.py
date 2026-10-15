from datetime import datetime

from app.models import Event


def update_event_status(event: Event):
    if event.event_status == "CANCELLED":
        return

    now = datetime.now()

    if now < event.event_date:
        event.event_status = "UPCOMING"
    elif now < event.event_end_date:
        event.event_status = "ONGOING"
    else:
        event.event_status = "COMPLETED"