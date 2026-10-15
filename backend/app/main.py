
from pathlib import Path

import app.models

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.schemas import EventResponse
from app.routes import (
    admin,
    auth,
    bookings,
    coupons,
    events,
    notifications,
    organizer,
    payments,
    reviews,
    tickets,
    availability,
    wishlist,
    event_updates,
    recommendations,
    profile,
    chatbot,
)


# =========================================================
# PATH CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_FOLDER = BASE_DIR / "static"
QR_FOLDER = STATIC_FOLDER / "qr"

STATIC_FOLDER.mkdir(parents=True, exist_ok=True)
QR_FOLDER.mkdir(parents=True, exist_ok=True)


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

# Create missing tables only; preserve existing data.
Base.metadata.create_all(bind=engine)


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="SmartEvent API",
    description=(
        "SmartEvent - Event Discovery and Ticket Booking Platform. "
        "Includes authentication, events, bookings, tickets, QR codes, "
        "notifications, organizer management, admin analytics, payments, "
        "coupons, reviews, availability, recommendations, wishlist, "
        "event updates, profiles, and chatbot."
    ),
    version="1.0.0",
)


# =========================================================
# CORS CONFIGURATION
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# STATIC FILES
# =========================================================

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_FOLDER)),
    name="static",
)


# =========================================================
# EXISTING API ROUTERS
# =========================================================

app.include_router(auth.router)
app.include_router(events.router)
app.include_router(bookings.router)
app.include_router(organizer.router)
app.include_router(tickets.router)
app.include_router(notifications.router)
app.include_router(admin.router)
app.include_router(payments.router)
app.include_router(coupons.router)
app.include_router(reviews.router)

app.include_router(availability.router)
app.include_router(wishlist.router)
app.include_router(event_updates.router)
app.include_router(profile.router)
app.include_router(chatbot.router)


# =========================================================
# MODULE 19: EVENT RECOMMENDATIONS
# =========================================================

# Register the existing recommendation handler once.
app.add_api_route(
    "/api/v1/events/recommendations",
    recommendations.get_recommendations,
    methods=["GET"],
    response_model=list[EventResponse],
    tags=["Event Recommendations"],
)


# =========================================================
# ROOT ENDPOINT
# =========================================================

@app.get("/", tags=["Health Check"])
def root():
    return {
        "message": "Welcome to SmartEvent API",
        "status": "running",
        "version": app.version,
        "modules": {
            "authentication": True,
            "events": True,
            "bookings": True,
            "organizer": True,
            "tickets": True,
            "notifications": True,
            "admin": True,
            "payments": True,
            "coupons": True,
            "reviews": True,
            "real_time_availability": True,
            "recommendations": True,
            "wishlist": True,
            "event_updates": True,
            "profile": True,
            "advanced_search": True,
            "chatbot": True,
        },
        "documentation": "/docs",
        "openapi_schema": "/openapi.json",
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health", tags=["Health Check"])
def health_check():
    return {
        "status": "healthy",
        "service": "SmartEvent API",
    }
