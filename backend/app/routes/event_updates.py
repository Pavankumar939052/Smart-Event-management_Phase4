from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.database import get_db
from app.dependencies import require_role
from app.models import Event, EventUpdate, User
from app.schemas import EventUpdateCreate, EventUpdateResponse

router = APIRouter(prefix="/api/v1/events", tags=["Module 21 - Live Event Updates"])

@router.get("/{event_id}/updates", response_model=list[EventUpdateResponse])
def list_updates(event_id: int, db: Session = Depends(get_db)):
    if not db.query(Event).filter(Event.id == event_id).first(): raise HTTPException(404, "Event not found.")
    return db.query(EventUpdate).filter(EventUpdate.event_id == event_id).order_by(EventUpdate.created_at.desc()).all()

@router.post("/{event_id}/updates", response_model=EventUpdateResponse, status_code=status.HTTP_201_CREATED)
def create_update(event_id: int, data: EventUpdateCreate, current_user: User = Depends(require_role("ORGANIZER", "ADMIN")), db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event: raise HTTPException(404, "Event not found.")
    if (current_user.role or "USER").upper() != "ADMIN" and event.organizer_id != current_user.id:
        raise HTTPException(403, "You can only post updates for your own events.")
    row = EventUpdate(event_id=event_id, user_id=current_user.id, message=data.message.strip())
    db.add(row); db.commit(); db.refresh(row); return row
