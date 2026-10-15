
import os
import uuid
from pathlib import Path

import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Booking, Ticket, User
from app.schemas import TicketResponse


router = APIRouter(
    prefix="/api/v1/tickets",
    tags=["Tickets"],
)


# =========================================================
# QR CODE STORAGE
# =========================================================

# This file is located at:
# backend/app/routes/tickets.py
#
# parents[0] = backend/app/routes
# parents[1] = backend/app
# parents[2] = backend

BASE_DIR = Path(__file__).resolve().parents[2]

QR_FOLDER = BASE_DIR / "static" / "qr"

# Create the QR folder automatically if it does not exist.
QR_FOLDER.mkdir(parents=True, exist_ok=True)


def create_qr_code(ticket_code: str) -> str:
    """
    Generate a QR image for a ticket and return its URL path.
    The ticket code is encoded into the QR image.
    """
    if not ticket_code:
        raise ValueError("Ticket code cannot be empty.")

    filename = f"{ticket_code}.png"
    filepath = QR_FOLDER / filename

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )

    qr.add_data(ticket_code)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    image.save(str(filepath))

    if not filepath.is_file() or filepath.stat().st_size == 0:
        raise RuntimeError("QR image was not saved successfully.")

    return f"/static/qr/{filename}"


def ensure_qr_code(ticket: Ticket) -> bool:
    """
    Ensure that a ticket has a valid QR image and URL.

    Returns True if the ticket's QR URL was changed.
    Does not create a new ticket or change its ticket code.
    """
    if not ticket.ticket_code:
        raise ValueError(
            f"Ticket ID {ticket.id} has no ticket code."
        )

    expected_url = f"/static/qr/{ticket.ticket_code}.png"
    filepath = QR_FOLDER / f"{ticket.ticket_code}.png"

    # Generate the image if it is missing or empty.
    if not filepath.is_file() or filepath.stat().st_size == 0:
        create_qr_code(ticket.ticket_code)

    changed = ticket.qr_code_url != expected_url

    if changed:
        ticket.qr_code_url = expected_url

    return changed


# =========================================================
# GENERATE OR REPAIR TICKETS FOR A CONFIRMED BOOKING
# =========================================================

@router.post(
    "/booking/{booking_id}",
    response_model=list[TicketResponse],
    status_code=status.HTTP_201_CREATED,
)
def generate_ticket(
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
            detail="Booking not found.",
        )

    if booking.booking_status != "CONFIRMED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tickets can only be generated for confirmed bookings.",
        )

    existing_tickets = (
        db.query(Ticket)
        .filter(Ticket.booking_id == booking.id)
        .order_by(Ticket.id.asc())
        .all()
    )

    # If the expected tickets already exist, repair their QR images.
    # Never create duplicate tickets for this booking.
    if len(existing_tickets) == booking.ticket_quantity:
        try:
            for ticket in existing_tickets:
                ensure_qr_code(ticket)

            db.commit()

            for ticket in existing_tickets:
                db.refresh(ticket)

            return existing_tickets

        except Exception as exc:
            db.rollback()

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to repair ticket QR codes.",
            ) from exc

    # Preserve existing tickets if the booking has an incomplete set.
    if existing_tickets:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This booking has an incomplete set of tickets. "
                "Existing ticket records were preserved."
            ),
        )

    created_files = []
    created_tickets = []

    try:
        for _ in range(booking.ticket_quantity):
            ticket_code = uuid.uuid4().hex.upper()

            qr_url = create_qr_code(ticket_code)
            filepath = QR_FOLDER / f"{ticket_code}.png"
            created_files.append(filepath)

            ticket = Ticket(
                booking_id=booking.id,
                ticket_code=ticket_code,
                qr_code_url=qr_url,
            )

            db.add(ticket)
            created_tickets.append(ticket)

        db.commit()

        for ticket in created_tickets:
            db.refresh(ticket)

        return created_tickets

    except Exception as exc:
        db.rollback()

        # Remove files created by this failed request only.
        for filepath in created_files:
            try:
                if filepath.is_file():
                    filepath.unlink()
            except OSError:
                pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate tickets.",
        ) from exc


# =========================================================
# GET CURRENT USER'S TICKETS
# =========================================================

@router.get(
    "/my",
    response_model=list[TicketResponse],
)
def get_my_tickets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tickets = (
        db.query(Ticket)
        .join(Booking, Ticket.booking_id == Booking.id)
        .filter(
            Booking.user_id == current_user.id,
            Booking.booking_status == "CONFIRMED",
        )
        .order_by(Ticket.id.asc())
        .all()
    )

    return tickets


# =========================================================
# REPAIR MISSING QR CODES FOR CURRENT USER
# =========================================================

@router.post("/my/repair-qr")
def repair_my_ticket_qr_codes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tickets = (
        db.query(Ticket)
        .join(Booking, Ticket.booking_id == Booking.id)
        .filter(
            Booking.user_id == current_user.id,
            Booking.booking_status == "CONFIRMED",
        )
        .order_by(Ticket.id.asc())
        .all()
    )

    repaired_count = 0

    try:
        for ticket in tickets:
            if ensure_qr_code(ticket):
                repaired_count += 1

        db.commit()

        return {
            "message": "QR code repair completed.",
            "repaired_count": repaired_count,
            "tickets_checked": len(tickets),
        }

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to repair QR codes.",
        ) from exc




