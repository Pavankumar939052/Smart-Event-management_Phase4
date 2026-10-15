
from app.database import SessionLocal
from app.models import Event

db = SessionLocal()

try:
    event = db.query(Event).filter(Event.id == 1).first()

    if event is None:
        print("Event ID 1 not found.")
    else:
        print(f"Event ID: {event.id}")
        print(f"Title: {event.title}")
        print(f"Total tickets: {event.total_tickets}")
        print(f"Available tickets: {event.available_tickets}")
        print(
            "Calculated sold tickets:",
            event.total_tickets - event.available_tickets,
        )
finally:
    db.close()
