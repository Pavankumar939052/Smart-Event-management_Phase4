
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, update
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    Booking,
    Event,
    Notification,
    Payment,
    Ticket,
    User,
)
from app.schemas import BookingCreate, BookingResponse
from app.realtime_availability import availability_manager


router = APIRouter(
    prefix="/api/v1/bookings",
    tags=["Bookings"],
)


async def broadcast_availability(event: Event) -> None:
    """Broadcast inventory changes without undoing a committed transaction."""
    try:
        await availability_manager.broadcast(
            event.id,
            {
                "type": "availability_update",
                "event_id": event.id,
                "total_tickets": event.total_tickets,
                "available_tickets": event.available_tickets,
                "is_available": event.available_tickets > 0,
            },
        )
    except Exception:
        # A WebSocket failure must not undo a successful database operation.
        pass


@router.post(
    "/",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_booking(
    request: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate the event and obtain its price.
    event = (
        db.query(Event)
        .filter(Event.id == request.event_id)
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found.",
        )

    if event.event_status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This event has been cancelled.",
        )

    if request.ticket_quantity <= 0 or request.ticket_quantity > 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ticket quantity must be between 1 and 10.",
        )

    try:
        # Atomically reserve tickets only when sufficient inventory exists.
        # This also permits older rows whose event_status is NULL.
        inventory_result = db.execute(
            update(Event)
            .where(
                Event.id == request.event_id,
                Event.available_tickets >= request.ticket_quantity,
                or_(
                    Event.event_status.is_(None),
                    Event.event_status != "CANCELLED",
                ),
            )
            .values(
                available_tickets=(
                    Event.available_tickets - request.ticket_quantity
                )
            )
            .execution_options(synchronize_session=False)
        )

        if inventory_result.rowcount != 1:
            db.rollback()

            # Re-check the latest event state for a helpful response.
            latest_event = (
                db.query(Event)
                .filter(Event.id == request.event_id)
                .first()
            )

            if latest_event is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Event not found.",
                )

            if latest_event.event_status == "CANCELLED":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This event has been cancelled.",
                )

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Not enough tickets available. "
                    "Please refresh availability."
                ),
            )

        # Inventory is reserved while payment is pending.
        booking = Booking(
            user_id=current_user.id,
            event_id=event.id,
            ticket_quantity=request.ticket_quantity,
            total_price=event.ticket_price * request.ticket_quantity,
            booking_status="PENDING",
        )

        db.add(booking)
        db.flush()

        notification = Notification(
            user_id=current_user.id,
            title="Booking Created",
            message=(
                f"Booking #{booking.id} for {event.title} was created. "
                "Complete payment to confirm it."
            ),
            type="BOOKING",
        )
        db.add(notification)

        # Booking, notification, and inventory change commit together.
        db.commit()
        db.refresh(booking)

        # Reload inventory after the atomic update.
        updated_event = (
            db.query(Event)
            .filter(Event.id == event.id)
            .first()
        )

        if updated_event is not None:
            await broadcast_availability(updated_event)

        return booking

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create booking.",
        )


@router.get(
    "/my",
    response_model=list[BookingResponse],
)
def get_my_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Booking)
        .filter(Booking.user_id == current_user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )


@router.patch("/{booking_id}/cancel")
async def cancel_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id,
            Booking.user_id == current_user.id,
        )
        .first()
    )

    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found for the current user.",
        )

    if booking.booking_status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already cancelled.",
        )

    successful_payment = (
        db.query(Payment)
        .filter(
            Payment.booking_id == booking.id,
            Payment.payment_status == "SUCCESS",
        )
        .first()
    )

    if successful_payment is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "This booking has already been paid. "
                "Refund handling is required before cancellation."
            ),
        )

    event_id = booking.event_id
    quantity = booking.ticket_quantity
    user_id = current_user.id
    booking_id_value = booking.id

    try:
        # Claim the cancellation atomically to prevent duplicate restoration.
        cancellation_result = db.execute(
            update(Booking)
            .where(
                Booking.id == booking_id_value,
                Booking.user_id == user_id,
                or_(
                    Booking.booking_status.is_(None),
                    Booking.booking_status != "CANCELLED",
                ),
            )
            .values(booking_status="CANCELLED")
            .execution_options(synchronize_session=False)
        )

        if cancellation_result.rowcount != 1:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Booking has already been cancelled.",
            )

        # Restore tickets without allowing inventory above the event capacity.
        inventory_result = db.execute(
            update(Event)
            .where(
                Event.id == event_id,
                Event.available_tickets + quantity <= Event.total_tickets,
            )
            .values(
                available_tickets=Event.available_tickets + quantity
            )
            .execution_options(synchronize_session=False)
        )

        if inventory_result.rowcount != 1:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Could not restore tickets safely. "
                    "Please contact support."
                ),
            )

        # Remove generated tickets for the cancelled booking.
        db.query(Ticket).filter(
            Ticket.booking_id == booking_id_value
        ).delete(synchronize_session=False)

        # A pending payment must not remain pending after cancellation.
        db.query(Payment).filter(
            Payment.booking_id == booking_id_value,
            Payment.payment_status == "PENDING",
        ).update(
            {"payment_status": "FAILED"},
            synchronize_session=False,
        )

        db.add(
            Notification(
                user_id=user_id,
                title="Booking Cancelled",
                message=(
                    f"Your booking #{booking_id_value} for "
                    f"event #{event_id} has been cancelled."
                ),
                type="BOOKING",
            )
        )

        db.commit()

        updated_event = (
            db.query(Event)
            .filter(Event.id == event_id)
            .first()
        )

        if updated_event is not None:
            await broadcast_availability(updated_event)

        return {
            "message": "Booking cancelled successfully.",
            "booking_id": booking_id_value,
            "event_id": event_id,
            "booking_status": "CANCELLED",
            "tickets_restored": quantity,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel booking.",
        )



