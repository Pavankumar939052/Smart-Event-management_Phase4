from app.database import SessionLocal
from app.models import Booking, Ticket

db = SessionLocal()

try:
    bookings = db.query(Booking).order_by(Booking.id.asc()).all()

    if not bookings:
        print("No bookings found.")

    for booking in bookings:
        ticket_count = (
            db.query(Ticket)
            .filter(Ticket.booking_id == booking.id)
            .count()
        )

        print(
            f"Booking ID: {booking.id} | "
            f"User ID: {booking.user_id} | "
            f"Event ID: {booking.event_id} | "
            f"Quantity: {booking.ticket_quantity} | "
            f"Status: {booking.booking_status} | "
            f"Tickets: {ticket_count}"
        )
finally:
    db.close()