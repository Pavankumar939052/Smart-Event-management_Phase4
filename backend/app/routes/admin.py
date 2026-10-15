
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import Booking, Event, Ticket, User


router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin Dashboard"],
)


# =========================================================
# REQUEST SCHEMA
# =========================================================

class RoleUpdate(BaseModel):
    role: Literal["USER", "ORGANIZER", "ADMIN"]


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def confirmed_bookings_query(db: Session):
    """
    Return confirmed bookings.

    Adjust the status value if your project uses a different
    spelling for confirmed bookings.
    """
    return db.query(Booking).filter(
        Booking.booking_status == "CONFIRMED"
    )


# =========================================================
# 1. VIEW ALL USERS — ADMIN ONLY
# =========================================================

@router.get("/users")
def get_all_users(
    admin: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.id.asc()).all()

    # Never return hashed passwords.
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at,
        }
        for user in users
    ]


# =========================================================
# 2. UPDATE A USER'S ROLE — ADMIN ONLY
# =========================================================

@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    data: RoleUpdate,
    admin: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    user.role = data.role

    try:
        db.commit()
        db.refresh(user)

        return {
            "message": "User role updated successfully.",
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
        }
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to update user role.",
        )


# =========================================================
# 3. VIEW ALL EVENTS — ADMIN ONLY
# =========================================================

@router.get("/events")
def get_all_events(
    admin: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    events = db.query(Event).order_by(Event.id.asc()).all()

    return [
        {
            "id": event.id,
            "title": event.title,
            "category": event.category,
            "location": event.location,
            "event_date": event.event_date,
            "event_end_date": event.event_end_date,
            "ticket_price": event.ticket_price,
            "total_tickets": event.total_tickets,
            "available_tickets": event.available_tickets,
            "organizer_id": event.organizer_id,
            "event_status": event.event_status,
        }
        for event in events
    ]


# =========================================================
# 4. VIEW ALL BOOKINGS — ADMIN ONLY
# =========================================================

@router.get("/bookings")
def get_all_bookings(
    admin: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    bookings = (
        db.query(Booking)
        .order_by(Booking.created_at.desc())
        .all()
    )

    return [
        {
            "id": booking.id,
            "user_id": booking.user_id,
            "event_id": booking.event_id,
            "ticket_quantity": booking.ticket_quantity,
            "total_price": booking.total_price,
            "booking_status": booking.booking_status,
            "created_at": booking.created_at,
        }
        for booking in bookings
    ]


# =========================================================
# 5. CANCEL AN EVENT — ADMIN ONLY
# =========================================================

@router.patch("/events/{event_id}/cancel")
def admin_cancel_event(
    event_id: int,
    admin: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    event = db.query(Event).filter(Event.id == event_id).first()

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Event not found.",
        )

    if event.event_status == "CANCELLED":
        raise HTTPException(
            status_code=400,
            detail="Event is already cancelled.",
        )

    try:
        event.event_status = "CANCELLED"
        db.commit()
        db.refresh(event)

        return {
            "message": "Event cancelled successfully.",
            "event_id": event.id,
            "event_status": event.event_status,
        }
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to cancel event.",
        )


# =========================================================
# 6. PLATFORM ANALYTICS — ADMIN ONLY
# =========================================================

@router.get("/analytics")
def get_admin_analytics(
    admin: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    total_users = db.query(func.count(User.id)).scalar() or 0

    total_events = db.query(func.count(Event.id)).scalar() or 0

    total_bookings = db.query(func.count(Booking.id)).scalar() or 0

    total_tickets_issued = (
        db.query(func.count(Ticket.id)).scalar() or 0
    )

    confirmed = confirmed_bookings_query(db)

    total_confirmed_bookings = confirmed.count()

    total_revenue = (
        confirmed.with_entities(
            func.coalesce(func.sum(Booking.total_price), 0)
        ).scalar()
        or 0
    )

    return {
        "total_users": total_users,
        "total_events": total_events,
        "total_bookings": total_bookings,
        "total_confirmed_bookings": total_confirmed_bookings,
        "total_tickets_issued": total_tickets_issued,
        "total_revenue": float(total_revenue),
    }


# =========================================================
# 7. DAILY TICKET SALES — ADMIN ONLY
# =========================================================

@router.get("/analytics/daily-sales")
def get_daily_ticket_sales(
    admin: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    # SQLite stores the booking timestamp as text/datetime.
    sale_date = func.date(Booking.created_at)

    results = (
        confirmed_bookings_query(db)
        .with_entities(
            sale_date.label("sale_date"),
            func.coalesce(
                func.sum(Booking.ticket_quantity), 0
            ).label("tickets_sold"),
            func.coalesce(
                func.sum(Booking.total_price), 0
            ).label("revenue"),
        )
        .group_by(sale_date)
        .order_by(sale_date.desc())
        .all()
    )

    return [
        {
            "date": str(row.sale_date),
            "tickets_sold": int(row.tickets_sold or 0),
            "revenue": float(row.revenue or 0),
        }
        for row in results
    ]


# =========================================================
# 8. MONTHLY BOOKING TRENDS — ADMIN ONLY
# =========================================================

@router.get("/analytics/monthly-bookings")
def get_monthly_booking_trends(
    admin: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    month = func.strftime("%Y-%m", Booking.created_at)

    results = (
        db.query(
            month.label("month"),
            func.count(Booking.id).label("booking_count"),
            func.coalesce(
                func.sum(Booking.total_price), 0
            ).label("revenue"),
        )
        .group_by(month)
        .order_by(month.desc())
        .all()
    )

    return [
        {
            "month": row.month,
            "booking_count": int(row.booking_count or 0),
            "revenue": float(row.revenue or 0),
        }
        for row in results
    ]


# =========================================================
# 9. POPULAR EVENTS — ADMIN ONLY
# =========================================================

@router.get("/analytics/popular-events")
def get_popular_events(
    admin: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    results = (
        confirmed_bookings_query(db)
        .join(Event, Booking.event_id == Event.id)
        .with_entities(
            Event.id.label("event_id"),
            Event.title.label("event_title"),
            func.coalesce(
                func.sum(Booking.ticket_quantity), 0
            ).label("tickets_sold"),
            func.count(Booking.id).label("booking_count"),
        )
        .group_by(Event.id, Event.title)
        .order_by(
            func.sum(Booking.ticket_quantity).desc()
        )
        .limit(10)
        .all()
    )

    return [
        {
            "event_id": row.event_id,
            "event_title": row.event_title,
            "tickets_sold": int(row.tickets_sold or 0),
            "booking_count": int(row.booking_count or 0),
        }
        for row in results
    ]


# =========================================================
# 10. TOP REVENUE EVENTS — ADMIN ONLY
# =========================================================

@router.get("/analytics/top-revenue-events")
def get_top_revenue_events(
    admin: User = Depends(require_role("ADMIN")),
    db: Session = Depends(get_db),
):
    results = (
        confirmed_bookings_query(db)
        .join(Event, Booking.event_id == Event.id)
        .with_entities(
            Event.id.label("event_id"),
            Event.title.label("event_title"),
            func.coalesce(
                func.sum(Booking.total_price), 0
            ).label("revenue"),
        )
        .group_by(Event.id, Event.title)
        .order_by(
            func.sum(Booking.total_price).desc()
        )
        .limit(10)
        .all()
    )

    return [
        {
            "event_id": row.event_id,
            "event_title": row.event_title,
            "revenue": float(row.revenue or 0),
        }
        for row in results
    ]
