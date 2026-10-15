
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import Booking, Event, User
from app.schemas import EventCreate, EventResponse, EventUpdate
from app.services.event_status import update_event_status


router = APIRouter(
    prefix="/api/v1/events",
    tags=["Events"],
)


# =========================================================
# HELPER — AUTOMATICALLY UPDATE EVENT STATUSES
# =========================================================

def sync_event_statuses(events: list[Event], db: Session):
    changed = False

    for event in events:
        previous_status = event.event_status

        # Do not overwrite a manually cancelled event.
        if previous_status == "CANCELLED":
            continue

        update_event_status(event)

        if event.event_status != previous_status:
            changed = True

    if changed:
        db.commit()


# =========================================================
# CREATE EVENT — ORGANIZER OR ADMIN
# =========================================================

@router.post(
    "/",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event(
    event_data: EventCreate,
    current_user: User = Depends(
        require_role("ORGANIZER", "ADMIN")
    ),
    db: Session = Depends(get_db),
):
    if event_data.event_end_date <= event_data.event_date:
        raise HTTPException(
            status_code=422,
            detail="event_end_date must be after event_date.",
        )

    event = Event(
        title=event_data.title,
        description=event_data.description,
        category=event_data.category,
        location=event_data.location,
        event_date=event_data.event_date,
        event_end_date=event_data.event_end_date,
        ticket_price=event_data.ticket_price,
        banner_image=event_data.banner_image,
        total_tickets=event_data.total_tickets,
        available_tickets=event_data.total_tickets,
        organizer_id=current_user.id,
        event_status="UPCOMING",
    )

    update_event_status(event)

    try:
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to create event.",
        )


# =========================================================
# GET ALL EVENTS — MODULE 16 SEARCH, FILTER AND SORT
# =========================================================

@router.get(
    "/",
    response_model=list[EventResponse],
)
def get_events(
    search: Optional[str] = Query(
        default=None,
        max_length=200,
        description="Search by event title",
    ),
    category: Optional[str] = Query(
        default=None,
        max_length=100,
        description="Filter by category",
    ),
    location: Optional[str] = Query(
        default=None,
        max_length=255,
        description="Filter by location",
    ),
    date_from: Optional[date] = Query(
        default=None,
        description="Start date in YYYY-MM-DD format",
    ),
    date_to: Optional[date] = Query(
        default=None,
        description="End date in YYYY-MM-DD format",
    ),
    min_price: Optional[float] = Query(default=None, ge=0, description="Minimum ticket price"),
    max_price: Optional[float] = Query(default=None, ge=0, description="Maximum ticket price"),
    sort_by: str = Query(
        default="date_asc",
        pattern="^(date_asc|date_desc|price_asc|price_desc|popularity)$",
        description=(
            "date_asc, date_desc, price_asc, "
            "price_desc, popularity"
        ),
    ),
    db: Session = Depends(get_db),
):
    # Validate the date range.
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=400,
            detail="date_from must be on or before date_to.",
        )

    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="min_price must be less than or equal to max_price.")

    query = db.query(Event)

    # Search event title.
    if search and search.strip():
        query = query.filter(
            Event.title.ilike(f"%{search.strip()}%")
        )

    # Filter category.
    if category and category.strip():
        if category.strip().lower() != "all":
            query = query.filter(
                Event.category.ilike(f"%{category.strip()}%")
            )

    # Filter location.
    if location and location.strip():
        query = query.filter(
            Event.location.ilike(f"%{location.strip()}%")
        )

    # Start date: include the selected day.
    if date_from:
        start_datetime = datetime.combine(
            date_from,
            time.min,
        )
        query = query.filter(
            Event.event_date >= start_datetime
        )

    # End date: include the entire selected day.
    if date_to:
        end_datetime = datetime.combine(
            date_to + timedelta(days=1),
            time.min,
        )
        query = query.filter(
            Event.event_date < end_datetime
        )

    if min_price is not None:
        query = query.filter(Event.ticket_price >= min_price)
    if max_price is not None:
        query = query.filter(Event.ticket_price <= max_price)

    # Sort results.
    if sort_by == "date_asc":
        query = query.order_by(
            Event.event_date.asc(),
            Event.id.asc(),
        )

    elif sort_by == "date_desc":
        query = query.order_by(
            Event.event_date.desc(),
            Event.id.desc(),
        )

    elif sort_by == "price_asc":
        query = query.order_by(
            Event.ticket_price.asc(),
            Event.id.asc(),
        )

    elif sort_by == "price_desc":
        query = query.order_by(
            Event.ticket_price.desc(),
            Event.id.desc(),
        )

    elif sort_by == "popularity":
        tickets_sold = (
            db.query(
                func.coalesce(
                    func.sum(Booking.ticket_quantity),
                    0,
                )
            )
            .filter(
                Booking.event_id == Event.id,
                Booking.booking_status != "CANCELLED",
            )
            .correlate(Event)
            .scalar_subquery()
        )

        query = query.order_by(
            tickets_sold.desc(),
            Event.event_date.asc(),
            Event.id.asc(),
        )

    events = query.all()

    sync_event_statuses(events, db)

    return events


# =========================================================
# GET ORGANIZER'S EVENTS — ORGANIZER ONLY
# =========================================================

@router.get(
    "/organizer/events",
    response_model=list[EventResponse],
)
def get_organizer_events(
    current_user: User = Depends(
        require_role("ORGANIZER")
    ),
    db: Session = Depends(get_db),
):
    events = (
        db.query(Event)
        .filter(Event.organizer_id == current_user.id)
        .order_by(Event.event_date.asc())
        .all()
    )

    sync_event_statuses(events, db)

    return events


# =========================================================
# UPDATE EVENT — OWNER OR ADMIN
# =========================================================

@router.put(
    "/{event_id}",
    response_model=EventResponse,
)
def update_event(
    event_id: int,
    event_data: EventUpdate,
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
            status_code=404,
            detail="Event not found.",
        )

    user_role = (current_user.role or "USER").upper()

    if (
        user_role != "ADMIN"
        and event.organizer_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You can only update your own events.",
        )

    changes = event_data.model_dump(exclude_unset=True)

    final_start = changes.get(
        "event_date",
        event.event_date,
    )
    final_end = changes.get(
        "event_end_date",
        event.event_end_date,
    )

    if (
        final_start is not None
        and final_end is not None
        and final_end <= final_start
    ):
        raise HTTPException(
            status_code=422,
            detail="event_end_date must be after event_date.",
        )

    if "total_tickets" in changes:
        new_total = changes["total_tickets"]

        if new_total is None or new_total < 0:
            raise HTTPException(
                status_code=400,
                detail="Total tickets must be zero or greater.",
            )

        tickets_sold = (
            event.total_tickets - event.available_tickets
        )

        if new_total < tickets_sold:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Total tickets cannot be less than "
                    "tickets already sold."
                ),
            )

        changes["available_tickets"] = new_total - tickets_sold

    try:
        for field, value in changes.items():
            setattr(event, field, value)

        update_event_status(event)

        db.commit()
        db.refresh(event)

        return event

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to update event.",
        )


# =========================================================
# CANCEL EVENT — OWNER OR ADMIN
# =========================================================

@router.patch(
    "/{event_id}/cancel",
    response_model=EventResponse,
)
def cancel_event(
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
            status_code=404,
            detail="Event not found.",
        )

    user_role = (current_user.role or "USER").upper()

    if (
        user_role != "ADMIN"
        and event.organizer_id != current_user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You can only cancel your own events.",
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

        return event

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to cancel event.",
        )


# =========================================================
# GET EVENT BY ID — PUBLIC
# =========================================================

@router.get(
    "/{event_id}",
    response_model=EventResponse,
)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
):
    event = (
        db.query(Event)
        .filter(Event.id == event_id)
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Event not found.",
        )

    sync_event_statuses([event], db)

    return event




