
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.database import Base


# =========================================================
# USER MODEL — RBAC
# Roles: USER, ORGANIZER, ADMIN
# =========================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)

    role = Column(
        String(20),
        default="USER",
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# =========================================================
# EVENT MODEL
# =========================================================

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    location = Column(String(255), nullable=False)

    event_date = Column(DateTime, nullable=False)
    event_end_date = Column(DateTime, nullable=True)

    ticket_price = Column(Float, nullable=False)
    banner_image = Column(String(500), nullable=True)

    total_tickets = Column(Integer, default=100, nullable=False)
    available_tickets = Column(Integer, default=100, nullable=False)

    organizer_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    # UPCOMING, ONGOING, COMPLETED, CANCELLED
    event_status = Column(
        String(20),
        default="UPCOMING",
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# =========================================================
# BOOKING MODEL
# =========================================================

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    event_id = Column(
        Integer,
        ForeignKey("events.id"),
        nullable=False,
        index=True,
    )

    ticket_quantity = Column(Integer, nullable=False)
    total_price = Column(Float, nullable=False)

    # PENDING_PAYMENT, CONFIRMED, CANCELLED
    booking_status = Column(
        String(30),
        default="CONFIRMED",
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# =========================================================
# TICKET MODEL
# =========================================================

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)

    booking_id = Column(
        Integer,
        ForeignKey("bookings.id"),
        nullable=False,
        index=True,
    )

    ticket_code = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    qr_code_url = Column(String(500), nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# =========================================================
# NOTIFICATION MODEL — MODULE 15
# =========================================================

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    # Keep the existing database column name "type".
    # Values: EVENT, BOOKING, PAYMENT, SYSTEM
    type = Column(
        String(20),
        default="SYSTEM",
        nullable=False,
        index=True,
    )

    is_read = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True,
    )


# =========================================================
# PAYMENT MODEL — MODULE 12
# =========================================================

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    booking_id = Column(
        Integer,
        ForeignKey("bookings.id"),
        nullable=False,
        index=True,
    )

    payment_method = Column(
        String(30),
        nullable=False,
        default="SIMULATED",
    )

    # PENDING, SUCCESS, FAILED
    payment_status = Column(
        String(20),
        nullable=False,
        default="PENDING",
        index=True,
    )

    transaction_id = Column(
        String(100),
        unique=True,
        nullable=True,
    )

    # Final amount after discount
    amount = Column(Float, nullable=False)

    coupon_code = Column(String(50), nullable=True)

    discount_amount = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# =========================================================
# COUPON MODEL — MODULE 13
# =========================================================

class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)

    code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    # PERCENTAGE or FIXED
    discount_type = Column(String(20), nullable=False)
    discount_value = Column(Float, nullable=False)

    minimum_amount = Column(
        Float,
        nullable=False,
        default=0.0,
    )

    expiry_date = Column(DateTime, nullable=True)

    # NULL means unlimited uses
    usage_limit = Column(Integer, nullable=True)

    used_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# =========================================================
# REVIEW MODEL — MODULE 14
# =========================================================

class Review(Base):
    __tablename__ = "reviews"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "event_id",
            name="uq_review_user_event",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    event_id = Column(
        Integer,
        ForeignKey("events.id"),
        nullable=False,
        index=True,
    )

    # Rating validation (1–5) belongs in the API schema.
    rating = Column(Integer, nullable=False)

    review_text = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )








# MODULE 20: saved events
class Wishlist(Base):
    __tablename__ = "wishlists"
    __table_args__ = (UniqueConstraint("user_id", "event_id", name="uq_wishlist_user_event"),)
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


# MODULE 21: organizer/admin event announcements
class EventUpdate(Base):
    __tablename__ = "event_updates"
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
