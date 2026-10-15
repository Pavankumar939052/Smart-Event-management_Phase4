
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import Booking, Event, User
from app.schemas import BookingResponse


router = APIRouter(
    prefix="/api/v1/organizer",
    tags=["Organizer"],
)


# =========================================================
# STEP 27: GET BOOKINGS FOR AN ORGANIZER'S OWN EVENT
# ORGANIZER only
# =========================================================

@router.get(
    "/events/{event_id}/bookings",
    response_model=list[BookingResponse],
)
def get_event_bookings(
    event_id: int,
    current_user: User = Depends(
        require_role("ORGANIZER")
    ),
    db: Session = Depends(get_db),
):
    event = (
        db.query(Event)
        .filter(Event.id == event_id)
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )

    if event.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view bookings for your own events.",
        )

    bookings = (
        db.query(Booking)
        .filter(Booking.event_id == event_id)
        .order_by(Booking.created_at.desc())
        .all()
    )

    return bookings


# =========================================================
# STEP 28: GET EVENT ANALYTICS
# ORGANIZER — OWN EVENTS ONLY
# ADMIN — ANY EVENT
# =========================================================

@router.get("/events/{event_id}/analytics")
def get_event_analytics(
    event_id: int,
    current_user: User = Depends(
        require_role("ORGANIZER", "ADMIN")
    ),
    db: Session = Depends(get_db),
):
    event = (
        db.query(Event)
        .filter(Event.id == event_id)
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )

    # Organizers can view only their own events.
    # Admins can view any event.
    if (
        current_user.role.upper() != "ADMIN"
        and event.organizer_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view analytics for your own events.",
        )

    # Count only confirmed bookings.
    total_bookings = (
        db.query(func.count(Booking.id))
        .filter(
            Booking.event_id == event_id,
            Booking.booking_status == "CONFIRMED",
        )
        .scalar()
        or 0
    )

    # Count tickets belonging to confirmed bookings.
    tickets_sold = (
        db.query(func.coalesce(func.sum(Booking.ticket_quantity), 0))
        .filter(
            Booking.event_id == event_id,
            Booking.booking_status == "CONFIRMED",
        )
        .scalar()
        or 0
    )

    return {
        "event_id": event.id,
        "event_title": event.title,
        "total_tickets": event.total_tickets,
        "tickets_sold": tickets_sold,
        "available_tickets": event.available_tickets,
        "total_bookings": total_bookings,
        "ticket_price": event.ticket_price,
        "estimated_revenue": tickets_sold * event.ticket_price,
    }


