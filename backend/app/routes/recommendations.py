
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Booking, Event, User
from app.schemas import EventResponse

router = APIRouter(
    prefix="/api/v1/events",
    tags=["Event Recommendations"],
)


@router.get(
    "/recommendations",
    response_model=list[EventResponse],
)
def get_recommendations(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Recommend upcoming events based on booking history."""

    now = datetime.now()

    user_bookings = (
        db.query(Booking.event_id, Event.category)
        .join(Event, Booking.event_id == Event.id)
        .filter(Booking.user_id == current_user.id)
        .filter(
            or_(
                Booking.booking_status.is_(None),
                Booking.booking_status != "CANCELLED",
            )
        )
        .all()
    )

    booked_event_ids = {event_id for event_id, _ in user_bookings}
    preferred_categories = list(
        dict.fromkeys(
            category for _, category in user_bookings if category
        )
    )

    query = db.query(Event).filter(
        Event.event_date >= now,
        or_(
            Event.event_status.is_(None),
            Event.event_status != "CANCELLED",
        ),
    )

    if booked_event_ids:
        query = query.filter(~Event.id.in_(booked_event_ids))

    if preferred_categories:
        query = query.order_by(
            Event.category.in_(preferred_categories).desc(),
            Event.event_date.asc(),
            Event.id.asc(),
        )
    else:
        query = query.order_by(
            Event.event_date.asc(),
            Event.id.asc(),
        )

    return query.limit(limit).all()

