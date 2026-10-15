from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.auth import get_current_user
from app.database import get_db
from app.models import Booking, Event, User
from app.schemas import ChatRequest

router = APIRouter(prefix="/api/v1/chatbot", tags=["Module 24 - AI Chatbot Assistant"])

def event_summary(e):
    return {"id":e.id,"title":e.title,"category":e.category,"location":e.location,"event_date":e.event_date,"ticket_price":e.ticket_price,"available_tickets":e.available_tickets}

@router.post("/chat")
def chat(data: ChatRequest, db: Session = Depends(get_db)):
    # This assistant is a deterministic local MVP and needs no external API key. Personal booking lookup is intentionally handled by a separate authenticated route.
    q=data.message.lower()
    if any(word in q for word in ["booking", "my ticket", "my tickets", "my reservation"]):
        return {"reply":"For privacy, sign in and open My Bookings to see your personal booking history.","suggestions":["Trending events","Find music events"]}
    query=db.query(Event).filter(Event.available_tickets > 0)
    category=next((c for c in ["music","tech","technology","sports","workshop","conference","art","comedy"] if c in q),None)
    if category: query=query.filter(Event.category.ilike(f"%{category}%"))
    location=next((loc for loc in ["bengaluru","bangalore","chennai","mumbai","delhi","hyderabad"] if loc in q),None)
    if location: query=query.filter(Event.location.ilike(f"%{location}%"))
    events=query.order_by(Event.event_date.asc()).limit(5).all()
    if events:
        return {"reply":"Here are some available events that may match your request:","events":[event_summary(e) for e in events],"suggestions":["Trending events","Find music events","Show my bookings"]}
    return {"reply":"I couldn't find matching available events. Try a category such as music, tech, sports, or a city name.","events":[],"suggestions":["Trending events","Find music events"]}

@router.get("/my-bookings")
def chatbot_my_bookings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows=db.query(Booking,Event).join(Event,Event.id==Booking.event_id).filter(Booking.user_id==current_user.id).order_by(Booking.created_at.desc()).limit(20).all()
    return [{"booking_id":b.id,"status":b.booking_status,"quantity":b.ticket_quantity,"total_price":b.total_price,"event":e.title,"event_date":e.event_date} for b,e in rows]
