from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.database import get_db
from app.models import Booking, Event, User
from app.schemas import ProfileUpdate, UserResponse

router = APIRouter(prefix="/api/v1/profile", tags=["Module 22 - User Profile"])

@router.get("/summary")
def profile_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    bookings = db.query(Booking).filter(Booking.user_id == current_user.id).all()
    return {"user": UserResponse.model_validate(current_user), "total_bookings": len(bookings),
            "confirmed_bookings": sum(b.booking_status == "CONFIRMED" for b in bookings),
            "cancelled_bookings": sum(b.booking_status == "CANCELLED" for b in bookings),
            "tickets_reserved": sum(b.ticket_quantity for b in bookings if b.booking_status != "CANCELLED")}

@router.patch("/", response_model=UserResponse)
def update_profile(data: ProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    changes = data.model_dump(exclude_unset=True)
    if not changes: return current_user
    if "email" in changes and db.query(User).filter(User.email == changes["email"], User.id != current_user.id).first():
        raise HTTPException(409, "Email is already in use.")
    if "username" in changes and db.query(User).filter(User.username == changes["username"], User.id != current_user.id).first():
        raise HTTPException(409, "Username is already in use.")
    for key,value in changes.items(): setattr(current_user,key,value)
    db.commit(); db.refresh(current_user); return current_user
