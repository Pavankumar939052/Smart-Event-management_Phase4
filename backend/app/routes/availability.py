from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models import Event
from app.realtime_availability import availability_manager

router = APIRouter(prefix="/api/v1/events", tags=["Module 18 - Real-Time Availability"])

@router.get("/{event_id}/availability")
def get_event_availability(event_id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found.")
    return {"event_id": event.id, "total_tickets": event.total_tickets,
            "available_tickets": event.available_tickets,
            "sold_tickets": event.total_tickets - event.available_tickets,
            "is_available": event.available_tickets > 0}

@router.websocket("/{event_id}/availability/ws")
async def event_availability_ws(websocket: WebSocket, event_id: int):
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if event is None:
            await websocket.close(code=1008, reason="Event not found")
            return
        initial = {"type": "availability_update", "event_id": event.id,
                   "total_tickets": event.total_tickets,
                   "available_tickets": event.available_tickets,
                   "is_available": event.available_tickets > 0}
    finally:
        db.close()
    await availability_manager.connect(event_id, websocket)
    try:
        await websocket.send_json(initial)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await availability_manager.disconnect(event_id, websocket)
