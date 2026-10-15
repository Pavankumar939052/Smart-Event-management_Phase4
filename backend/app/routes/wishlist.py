from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.database import get_db
from app.models import Event, User, Wishlist
from app.schemas import WishlistResponse, EventResponse

router = APIRouter(prefix="/api/v1/wishlist", tags=["Module 20 - Wishlist"])

@router.get("/", response_model=list[dict])
def get_wishlist(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Wishlist, Event).join(Event, Event.id == Wishlist.event_id).filter(Wishlist.user_id == current_user.id).order_by(Wishlist.created_at.desc()).all()
    return [{"id": w.id, "event_id": e.id, "created_at": w.created_at,
             "title": e.title, "description": e.description, "category": e.category,
             "location": e.location, "event_date": e.event_date, "ticket_price": e.ticket_price,
             "banner_image": e.banner_image, "available_tickets": e.available_tickets,
             "total_tickets": e.total_tickets, "event_status": e.event_status} for w, e in rows]

@router.post("/{event_id}", response_model=WishlistResponse, status_code=status.HTTP_201_CREATED)
def add_to_wishlist(event_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event: raise HTTPException(status_code=404, detail="Event not found.")
    row = db.query(Wishlist).filter(Wishlist.user_id == current_user.id, Wishlist.event_id == event_id).first()
    if row: return row
    row = Wishlist(user_id=current_user.id, event_id=event_id)
    db.add(row)
    try:
        db.commit(); db.refresh(row); return row
    except Exception:
        db.rollback(); raise HTTPException(status_code=409, detail="Event is already in your wishlist.")

@router.delete("/{event_id}")
def remove_from_wishlist(event_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(Wishlist).filter(Wishlist.user_id == current_user.id, Wishlist.event_id == event_id).first()
    if not row: raise HTTPException(status_code=404, detail="Event not found in your wishlist.")
    db.delete(row); db.commit(); return {"message": "Event removed from wishlist."}
